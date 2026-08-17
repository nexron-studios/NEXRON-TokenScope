//! Startparameter der Desktop-Hülle.
//!
//! Jede Option lässt sich über die Kommandozeile oder eine Umgebungsvariable
//! setzen; die Kommandozeile gewinnt. Das erlaubt eine Verknüpfung mit
//! `--monitor 4` genauso wie einen Start aus `start.ps1`.

use std::path::PathBuf;

/// Auswahl über die Bildschirmfläche statt über Nummer oder Name.
#[derive(Clone, Copy, PartialEq)]
pub enum BySize {
    Smallest,
    Largest,
}

#[derive(Clone)]
pub struct Options {
    /// Port, auf dem das FastAPI-Backend lauscht.
    pub port: u16,
    /// 1-basierte Monitornummer; `0` überlässt die Platzierung dem System.
    pub monitor: usize,
    /// Alternative zur Nummer: ein Stück des Gerätenamens (z. B. `DISPLAY4`).
    /// Robuster, weil sich die Reihenfolge beim An- und Abstecken ändert.
    pub monitor_name: Option<String>,
    /// Noch robuster für einen festen Nebenschirm: nach Fläche auswählen.
    pub monitor_size: Option<BySize>,
    pub fullscreen: bool,
    pub always_on_top: bool,
    /// Ob ein fehlendes Backend selbst gestartet werden darf.
    pub spawn_backend: bool,
    /// Nur die erkannten Monitore anzeigen und sonst nichts tun.
    pub list_monitors: bool,
    /// Projektwurzel; ohne Angabe wird sie gesucht.
    pub root: Option<PathBuf>,
}

impl Default for Options {
    fn default() -> Self {
        Self {
            port: 8787,
            monitor: 0,
            monitor_name: None,
            monitor_size: None,
            fullscreen: true,
            always_on_top: false,
            spawn_backend: true,
            list_monitors: false,
            root: None,
        }
    }
}

impl Options {
    pub fn from_env_and_args() -> Self {
        let mut options = Self::default();

        if let Some(port) = env_number("NEXRON_TOKENSCOPE_PORT") {
            options.port = port as u16;
        }
        if let Ok(monitor) = std::env::var("NEXRON_TOKENSCOPE_DESKTOP_MONITOR") {
            options.set_monitor(&monitor);
        }
        if env_flag("NEXRON_TOKENSCOPE_DESKTOP_WINDOWED") {
            options.fullscreen = false;
        }
        if env_flag("NEXRON_TOKENSCOPE_DESKTOP_ON_TOP") {
            options.always_on_top = true;
        }
        if let Ok(root) = std::env::var("NEXRON_TOKENSCOPE_ROOT") {
            if !root.is_empty() {
                options.root = Some(PathBuf::from(root));
            }
        }

        let args: Vec<String> = std::env::args().skip(1).collect();
        let mut i = 0;
        while i < args.len() {
            match args[i].as_str() {
                "--port" => {
                    if let Some(value) = args.get(i + 1).and_then(|v| v.parse().ok()) {
                        options.port = value;
                    }
                    i += 1;
                }
                "--monitor" => {
                    if let Some(value) = args.get(i + 1) {
                        options.set_monitor(value);
                    }
                    i += 1;
                }
                "--root" => {
                    if let Some(value) = args.get(i + 1) {
                        options.root = Some(PathBuf::from(value));
                    }
                    i += 1;
                }
                "--windowed" => options.fullscreen = false,
                "--fullscreen" => options.fullscreen = true,
                "--on-top" => options.always_on_top = true,
                "--no-backend" => options.spawn_backend = false,
                "--list-monitors" => options.list_monitors = true,
                _ => {}
            }
            i += 1;
        }

        options
    }

    /// Zahlen sind Positionen in der Monitorliste, `smallest`/`largest`
    /// wählen nach Fläche, alles andere ist ein Stück des Gerätenamens.
    fn set_monitor(&mut self, value: &str) {
        let value = value.trim();
        if value.is_empty() {
            return;
        }

        self.monitor = 0;
        self.monitor_name = None;
        self.monitor_size = None;

        match value.to_ascii_lowercase().as_str() {
            "smallest" | "kleinster" => self.monitor_size = Some(BySize::Smallest),
            "largest" | "groesster" | "größter" => self.monitor_size = Some(BySize::Largest),
            lowered => match lowered.parse::<usize>() {
                Ok(index) => self.monitor = index,
                Err(_) => self.monitor_name = Some(lowered.to_string()),
            },
        }
    }
}

fn env_number(name: &str) -> Option<u32> {
    std::env::var(name).ok()?.trim().parse().ok()
}

fn env_flag(name: &str) -> bool {
    matches!(
        std::env::var(name).unwrap_or_default().trim(),
        "1" | "true" | "True" | "yes"
    )
}
