// Im Release soll kein Konsolenfenster mitlaufen; im Debug ist es nützlich.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

//! Desktop-Hülle für NEXRON-TokenScope.
//!
//! Die Hülle rendert das Frontend nicht selbst: Sie startet bei Bedarf das
//! FastAPI-Backend und zeigt dessen ausgelieferte Oberfläche
//! (`http://127.0.0.1:<port>/`) in einem Vollbildfenster auf einem wählbaren
//! Monitor. Dadurch bleibt alles gleichursprünglich, und am Frontend musste
//! für den Desktop-Betrieb nichts geändert werden.

mod backend;
mod options;

use std::sync::Mutex;
use std::time::Duration;

use tauri::{
    AppHandle, Manager, PhysicalPosition, PhysicalSize, RunEvent, WebviewUrl, WebviewWindow,
    WebviewWindowBuilder, WindowEvent,
};
use tauri_plugin_global_shortcut::{Code, GlobalShortcutExt, Shortcut, ShortcutState};

use backend::Backend;
use options::{BySize, Options};

/// Größe des Splash-Fensters in logischen Pixeln.
const SPLASH_SIZE: (f64, f64) = (460.0, 320.0);

/// Wie lange auf einen antwortenden Port gewartet wird, bevor der Start als
/// gescheitert gilt. Der erste Lauf braucht am längsten, weil Python die
/// Abhängigkeiten erst importieren muss.
const STARTUP_TIMEOUT: Duration = Duration::from_secs(120);

/// Ein Monitor in der Reihenfolge, in der das System ihn meldet – genau diese
/// 1-basierte Nummer erwartet `--monitor`.
struct Screen {
    index: usize,
    name: String,
    position: PhysicalPosition<i32>,
    size: PhysicalSize<u32>,
}

/// Hält den selbst gestarteten Backend-Prozess, damit er beim Beenden der App
/// nicht verwaist weiterläuft.
struct BackendProcess(Mutex<Option<Backend>>);

fn main() {
    let options = Options::from_env_and_args();

    let app = tauri::Builder::default()
        .plugin(
            tauri_plugin_global_shortcut::Builder::new()
                .with_handler(|app, shortcut, event| {
                    if event.state() == ShortcutState::Pressed {
                        handle_shortcut(app, shortcut);
                    }
                })
                .build(),
        )
        .manage(BackendProcess(Mutex::new(None)))
        .setup(move |app| {
            let handle = app.handle().clone();
            let options = options.clone();

            let splash = build_splash(&handle)?;
            let screens = enumerate_screens(&splash);
            let target = pick_screen(&screens, &options);

            log(&handle, &format!("{} Monitor(e) erkannt", screens.len()));
            for screen in &screens {
                log(
                    &handle,
                    &format!(
                        "  [{}] {} {}x{} @ {},{}",
                        screen.index,
                        screen.name,
                        screen.size.width,
                        screen.size.height,
                        screen.position.x,
                        screen.position.y
                    ),
                );
            }

            match target {
                Some(screen) => {
                    log(
                        &handle,
                        &format!("Zielbildschirm: [{}] {}", screen.index, screen.name),
                    );
                    center_on(&splash, screen, SPLASH_SIZE);
                }
                None => {
                    if let Some(wanted) = describe_wanted(&options) {
                        log(
                            &handle,
                            &format!("{wanted} gibt es nicht – nutze den primären Bildschirm"),
                        );
                    }
                }
            }

            if options.list_monitors {
                show_monitor_list(&splash, &screens, target.map(|s| s.index));
                set_status(&splash, "Monitorübersicht – Nummer für --monitor merken");
                set_hint(&splash, "Fenster mit Alt+F4 schließen");
                return Ok(());
            }

            let bounds = target.map(|s| (s.position, s.size));
            std::thread::spawn(move || start_and_open(handle, options, bounds));
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("Tauri-App konnte nicht erstellt werden");

    app.run(|handle, event| {
        if let RunEvent::Exit = event {
            if let Some(backend) = handle.state::<BackendProcess>().0.lock().unwrap().take() {
                backend.stop();
            }
        }
    });
}

/// Startet das Backend (falls nötig), wartet auf den Port und öffnet erst dann
/// das eigentliche Fenster. Läuft im Hintergrund-Thread.
fn start_and_open(
    handle: AppHandle,
    options: Options,
    bounds: Option<(PhysicalPosition<i32>, PhysicalSize<u32>)>,
) {
    let splash = handle.get_webview_window("splash");
    let status = |text: &str| {
        if let Some(window) = &splash {
            set_status(window, text);
        }
        log(&handle, text);
    };

    if backend::port_is_open(options.port) {
        status(&format!(
            "Backend läuft bereits auf Port {} – verbinde",
            options.port
        ));
    } else if !options.spawn_backend {
        status(&format!(
            "Auf Port {} lauscht nichts, und --no-backend verbietet den Start",
            options.port
        ));
        return;
    } else {
        match backend::locate_root(options.root.clone()) {
            Some(root) => {
                status("Starte das Backend …");
                match backend::spawn(&root, options.port) {
                    Ok(child) => {
                        *handle.state::<BackendProcess>().0.lock().unwrap() = Some(child);
                        log(&handle, &format!("Backend gestartet aus {}", root.display()));
                    }
                    Err(err) => {
                        status(&format!("Backend ließ sich nicht starten: {err}"));
                        return;
                    }
                }
            }
            None => {
                status("Projektordner nicht gefunden – bitte NEXRON_TOKENSCOPE_ROOT setzen");
                return;
            }
        }
    }

    status("Warte auf das Backend …");
    if let Err(err) = wait_for_backend(&handle, options.port) {
        status(&err);
        return;
    }

    if let Some(window) = &splash {
        set_hint(window, "F11 schaltet den Vollbildmodus um");
    }
    status("Öffne das Dashboard …");
    let url = format!("http://127.0.0.1:{}/", options.port);
    let _ = handle.clone().run_on_main_thread(move || {
        match build_main_window(&handle, &url, &options, bounds) {
            Ok(_) => {
                if let Some(window) = handle.get_webview_window("splash") {
                    let _ = window.close();
                }
            }
            Err(err) => {
                if let Some(window) = handle.get_webview_window("splash") {
                    set_status(&window, &format!("Fenster ließ sich nicht öffnen: {err}"));
                }
            }
        }
    });
}

/// Pollt den Port, bricht aber ab, sobald ein selbst gestartetes Backend
/// gestorben ist – sonst liefe die Wartezeit ins Leere.
fn wait_for_backend(handle: &AppHandle, port: u16) -> Result<(), String> {
    let deadline = std::time::Instant::now() + STARTUP_TIMEOUT;

    while std::time::Instant::now() < deadline {
        if backend::port_is_open(port) {
            return Ok(());
        }

        let state = handle.state::<BackendProcess>();
        let mut guard = state.0.lock().unwrap();
        if let Some(child) = guard.as_mut() {
            if let Some(code) = child.exited() {
                return Err(format!(
                    "Das Backend hat sich beendet (Code {code}). Läuft `start.ps1` einmal ohne Fehler durch?"
                ));
            }
        }
        drop(guard);

        std::thread::sleep(Duration::from_millis(250));
    }

    Err(format!(
        "Das Backend antwortet nach {} Sekunden nicht auf Port {port}",
        STARTUP_TIMEOUT.as_secs()
    ))
}

fn build_splash(handle: &AppHandle) -> tauri::Result<WebviewWindow> {
    WebviewWindowBuilder::new(handle, "splash", WebviewUrl::App("index.html".into()))
        .title("NEXRON-TokenScope")
        .inner_size(SPLASH_SIZE.0, SPLASH_SIZE.1)
        .resizable(false)
        .center()
        .build()
}

fn build_main_window(
    handle: &AppHandle,
    url: &str,
    options: &Options,
    bounds: Option<(PhysicalPosition<i32>, PhysicalSize<u32>)>,
) -> Result<WebviewWindow, String> {
    let parsed = tauri::Url::parse(url).map_err(|err| err.to_string())?;

    let window = WebviewWindowBuilder::new(handle, "main", WebviewUrl::External(parsed))
        .title("NEXRON-TokenScope")
        .inner_size(1280.0, 800.0)
        .always_on_top(options.always_on_top)
        .visible(false)
        .build()
        .map_err(|err| err.to_string())?;

    // Die Tastenkuerzel gelten nur, solange das Fenster vorn ist – sonst
    // naehme die Huelle anderen Programmen F11 und Esc weg.
    let focus_handle = handle.clone();
    window.on_window_event(move |event| {
        if let WindowEvent::Focused(focused) = event {
            set_view_shortcuts(&focus_handle, *focused);
        }
    });

    // Erst auf den Zielmonitor setzen: Windows macht das Fenster auf dem
    // Bildschirm gross, auf dem es gerade steht.
    if let Some((position, size)) = bounds {
        let _ = window.set_position(position);
        let _ = window.set_size(size);
    }

    let _ = window.show();
    let _ = window.set_focus();
    set_view_shortcuts(handle, true);

    if options.fullscreen {
        // Vor dem Anzeigen nimmt Windows den Befehl nur manchmal an.
        let _ = window.set_fullscreen(true);
        confirm_fullscreen(handle.clone());
    }

    Ok(window)
}

/// Faesst kurz nach dem Oeffnen noch einmal nach und haelt im Log fest, was
/// dabei herauskam – ein Fenster, das den Vollbildbefehl verschluckt hat,
/// faellt sonst niemandem auf.
fn confirm_fullscreen(handle: AppHandle) {
    std::thread::spawn(move || {
        std::thread::sleep(Duration::from_millis(400));

        let inner = handle.clone();
        let _ = handle.run_on_main_thread(move || {
            let Some(window) = inner.get_webview_window("main") else {
                return;
            };
            if !window.is_fullscreen().unwrap_or(false) {
                let _ = window.set_fullscreen(true);
            }
            log(
                &inner,
                &format!("Vollbild: {}", window.is_fullscreen().unwrap_or(false)),
            );
        });
    });
}

/// Vollbild ohne Ausweg waere eine Falle: Das Fenster hat dann keine
/// Titelleiste mehr. F11 schaltet um, Esc führt zurueck.
fn set_view_shortcuts(handle: &AppHandle, active: bool) {
    let manager = handle.global_shortcut();

    for code in [Code::F11, Code::Escape] {
        let shortcut = Shortcut::new(None, code);
        if active {
            if !manager.is_registered(shortcut) {
                let _ = manager.register(shortcut);
            }
        } else {
            let _ = manager.unregister(shortcut);
        }
    }
}

fn handle_shortcut(handle: &AppHandle, shortcut: &Shortcut) {
    let Some(window) = handle.get_webview_window("main") else {
        return;
    };
    let fullscreen = window.is_fullscreen().unwrap_or(false);

    match shortcut.key {
        Code::F11 => {
            let _ = window.set_fullscreen(!fullscreen);
        }
        // Esc soll nur herausführen, nicht hinein – sonst waere die Taste in
        // der Oberflaeche nicht mehr benutzbar.
        Code::Escape if fullscreen => {
            let _ = window.set_fullscreen(false);
        }
        _ => {}
    }
}

fn enumerate_screens(window: &WebviewWindow) -> Vec<Screen> {
    window
        .available_monitors()
        .unwrap_or_default()
        .into_iter()
        .enumerate()
        .map(|(i, monitor)| Screen {
            index: i + 1,
            name: monitor
                .name()
                .cloned()
                .unwrap_or_else(|| format!("Monitor {}", i + 1)),
            position: *monitor.position(),
            size: *monitor.size(),
        })
        .collect()
}

/// Ohne jede Angabe überlässt die Hülle die Platzierung dem System.
fn pick_screen<'a>(screens: &'a [Screen], options: &Options) -> Option<&'a Screen> {
    if let Some(by_size) = options.monitor_size {
        let area = |screen: &&Screen| {
            u64::from(screen.size.width) * u64::from(screen.size.height)
        };
        return match by_size {
            BySize::Smallest => screens.iter().min_by_key(area),
            BySize::Largest => screens.iter().max_by_key(area),
        };
    }
    if let Some(name) = &options.monitor_name {
        return screens
            .iter()
            .find(|screen| screen.name.to_ascii_lowercase().contains(name));
    }
    if options.monitor == 0 {
        return None;
    }
    screens.iter().find(|screen| screen.index == options.monitor)
}

fn describe_wanted(options: &Options) -> Option<String> {
    if options.monitor_size.is_some() {
        return Some("Ein Bildschirm".into());
    }
    match (&options.monitor_name, options.monitor) {
        (Some(name), _) => Some(format!("Ein Monitor mit »{name}« im Namen")),
        (None, 0) => None,
        (None, index) => Some(format!("Monitor {index}")),
    }
}

fn center_on(window: &WebviewWindow, screen: &Screen, logical_size: (f64, f64)) {
    let scale = window.scale_factor().unwrap_or(1.0);
    let width = (logical_size.0 * scale) as i32;
    let height = (logical_size.1 * scale) as i32;

    let _ = window.set_position(PhysicalPosition::new(
        screen.position.x + (screen.size.width as i32 - width) / 2,
        screen.position.y + (screen.size.height as i32 - height) / 2,
    ));
}

fn show_monitor_list(window: &WebviewWindow, screens: &[Screen], selected: Option<usize>) {
    let payload: Vec<serde_json::Value> = screens
        .iter()
        .map(|screen| {
            serde_json::json!({
                "index": screen.index,
                "name": screen.name,
                "width": screen.size.width,
                "height": screen.size.height,
                "x": screen.position.x,
                "y": screen.position.y,
            })
        })
        .collect();

    let _ = window.eval(&format!(
        "window.__showMonitors({}, {})",
        serde_json::to_string(&payload).unwrap_or_else(|_| "[]".into()),
        selected.map_or("null".to_string(), |i| i.to_string())
    ));
}

fn set_status(window: &WebviewWindow, text: &str) {
    let _ = window.eval(&format!(
        "window.__setStatus && window.__setStatus({})",
        serde_json::Value::from(text)
    ));
}

fn set_hint(window: &WebviewWindow, text: &str) {
    let _ = window.eval(&format!(
        "window.__setHint && window.__setHint({})",
        serde_json::Value::from(text)
    ));
}

/// Ohne Konsolenfenster ist die Logdatei die einzige Spur, die ein
/// fehlgeschlagener Start hinterlässt.
fn log(handle: &AppHandle, message: &str) {
    use std::io::Write;

    let Ok(dir) = handle.path().app_log_dir() else {
        return;
    };
    if std::fs::create_dir_all(&dir).is_err() {
        return;
    }

    if let Ok(mut file) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(dir.join("desktop.log"))
    {
        let _ = writeln!(file, "{message}");
    }
}
