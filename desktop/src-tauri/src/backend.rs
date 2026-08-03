//! Start und Überwachung des FastAPI-Backends.
//!
//! Die Hülle bündelt kein eigenes Python: Sie sucht die Projektwurzel und
//! benutzt die dort bereits eingerichtete virtuelle Umgebung. Läuft der Dienst
//! schon (etwa über `start.ps1`), wird gar nichts gestartet.

use std::io;
use std::net::{Ipv4Addr, SocketAddr, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Child, Command};
use std::time::Duration;

#[cfg(windows)]
const CREATE_NO_WINDOW: u32 = 0x0800_0000;

pub struct Backend {
    child: Child,
    /// Solange dieses Handle lebt, lebt das Job-Objekt – und mit dessen
    /// Ende stirbt das Backend. Wird nie gelesen, nur gehalten.
    #[cfg(windows)]
    _job: Option<job::Job>,
}

impl Backend {
    /// `Some(code)`, sobald sich der Prozess beendet hat.
    pub fn exited(&mut self) -> Option<i32> {
        match self.child.try_wait() {
            Ok(Some(status)) => Some(status.code().unwrap_or(-1)),
            _ => None,
        }
    }

    pub fn stop(mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

/// Uvicorn öffnet den Socket erst nach dem Anwendungsstart – eine
/// erfolgreiche Verbindung heißt also wirklich „bereit“.
pub fn port_is_open(port: u16) -> bool {
    let address = SocketAddr::from((Ipv4Addr::LOCALHOST, port));
    TcpStream::connect_timeout(&address, Duration::from_millis(400)).is_ok()
}

/// Sucht den Ordner, der `backend/app/main.py` enthält – erst neben der
/// ausführbaren Datei, dann neben dem Arbeitsverzeichnis.
pub fn locate_root(explicit: Option<PathBuf>) -> Option<PathBuf> {
    if let Some(root) = explicit {
        return is_project_root(&root).then_some(root);
    }

    let starts = [
        std::env::current_exe()
            .ok()
            .and_then(|exe| exe.parent().map(Path::to_path_buf)),
        std::env::current_dir().ok(),
    ];

    for start in starts.into_iter().flatten() {
        for candidate in start.ancestors() {
            if is_project_root(candidate) {
                return Some(candidate.to_path_buf());
            }
        }
    }

    None
}

fn is_project_root(path: &Path) -> bool {
    path.join("backend").join("app").join("main.py").is_file()
}

pub fn spawn(root: &Path, port: u16) -> io::Result<Backend> {
    let backend_dir = root.join("backend");
    let mut command = Command::new(python_for(&backend_dir));

    command
        .args([
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            &port.to_string(),
        ])
        .current_dir(&backend_dir)
        .env("PYTHONPATH", &backend_dir);

    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        command.creation_flags(CREATE_NO_WINDOW);
    }

    let child = command.spawn()?;

    // Ein sauberes Beenden raeumt den Prozess ohnehin ab. Das Job-Objekt
    // greift in den anderen Faellen: Absturz, Taskmanager, kill -9.
    #[cfg(windows)]
    let job = job::confine(&child);

    Ok(Backend {
        child,
        #[cfg(windows)]
        _job: job,
    })
}

/// Windows kennt kein „Kind stirbt mit dem Elternprozess“. Ein Job-Objekt mit
/// `KILL_ON_JOB_CLOSE` ist der uebliche Ersatz: Faellt der letzte Verweis auf
/// den Job weg – spaetestens, wenn Windows die Handles des beendeten Prozesses
/// schliesst – nimmt der Kernel alle Mitglieder mit.
#[cfg(windows)]
mod job {
    use std::os::windows::io::AsRawHandle;
    use std::process::Child;

    use windows::Win32::Foundation::{CloseHandle, HANDLE};
    use windows::Win32::System::JobObjects::{
        AssignProcessToJobObject, CreateJobObjectW, JobObjectExtendedLimitInformation,
        SetInformationJobObject, JOBOBJECT_EXTENDED_LIMIT_INFORMATION,
        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
    };

    pub struct Job(HANDLE);

    impl Drop for Job {
        fn drop(&mut self) {
            unsafe {
                let _ = CloseHandle(self.0);
            }
        }
    }

    // Das Handle wird nur gehalten und am Ende geschlossen.
    unsafe impl Send for Job {}

    pub fn confine(child: &Child) -> Option<Job> {
        unsafe {
            let handle = CreateJobObjectW(None, windows::core::PCWSTR::null()).ok()?;
            let job = Job(handle);

            let mut limits = JOBOBJECT_EXTENDED_LIMIT_INFORMATION::default();
            limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
            SetInformationJobObject(
                handle,
                JobObjectExtendedLimitInformation,
                &limits as *const _ as *const core::ffi::c_void,
                size_of::<JOBOBJECT_EXTENDED_LIMIT_INFORMATION>() as u32,
            )
            .ok()?;

            AssignProcessToJobObject(handle, HANDLE(child.as_raw_handle() as _)).ok()?;
            Some(job)
        }
    }
}

/// Bevorzugt die venv des Projekts; ohne sie bleibt nur das Python aus dem PATH.
fn python_for(backend_dir: &Path) -> PathBuf {
    let venv = backend_dir.join(".venv");
    let candidates = if cfg!(windows) {
        [venv.join("Scripts").join("python.exe"), venv.join("bin").join("python")]
    } else {
        [venv.join("bin").join("python"), venv.join("bin").join("python3")]
    };

    candidates
        .into_iter()
        .find(|path| path.is_file())
        .unwrap_or_else(|| PathBuf::from(if cfg!(windows) { "python" } else { "python3" }))
}
