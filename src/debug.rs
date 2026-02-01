//! Debug logging utilities for troubleshooting.
//!
//! All debug output is controlled by the `debug` feature flag.
//! To enable debug output, build with: `cargo build --features debug`

/// Print debug message (stderr) - only when `debug` feature is enabled
#[macro_export]
macro_rules! debug {
    ($($arg:tt)*) => {
        #[cfg(feature = "debug")]
        {
            eprintln!($($arg)*);
            $crate::debug::log_to_file(&format!($($arg)*));
        }
    };
}

/// Print debug message without newline - only when `debug` feature is enabled
#[macro_export]
macro_rules! debug_print {
    ($($arg:tt)*) => {
        #[cfg(feature = "debug")]
        eprint!($($arg)*)
    };
}

/// Print section header - only when `debug` feature is enabled
#[macro_export]
macro_rules! debug_section {
    ($title:expr) => {
        #[cfg(feature = "debug")]
        eprintln!("\n▶▶▶ {} ◀◀◀", $title)
    };
}

/// Print subsection - only when `debug` feature is enabled
#[macro_export]
macro_rules! debug_subsection {
    ($title:expr) => {
        #[cfg(feature = "debug")]
        eprintln!("  > {}", $title)
    };
}

/// Debug enter function - only when `debug` feature is enabled
#[macro_export]
macro_rules! debug_enter {
    ($func:expr) => {
        #[cfg(feature = "debug")]
        {
            eprintln!("[ENTER] {}", $func);
            $crate::debug::log_to_file(&format!("[ENTER] {}", $func));
        }
    };
}

/// Debug exit function - only when `debug` feature is enabled
#[macro_export]
macro_rules! debug_exit {
    ($func:expr) => {
        #[cfg(feature = "debug")]
        {
            eprintln!("[EXIT] {}", $func);
            $crate::debug::log_to_file(&format!("[EXIT] {}", $func));
        }
    };
}

/// Debug variable dump - only when `debug` feature is enabled
#[macro_export]
macro_rules! debug_var {
    ($name:expr, $val:expr) => {
        #[cfg(feature = "debug")]
        {
            eprintln!("[VAR] {} = {:?}", $name, $val);
            $crate::debug::log_to_file(&format!("[VAR] {} = {:?}", $name, $val));
        }
    };
}

use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::PathBuf;
use std::sync::Mutex;

/// Global log file handle (protected by mutex for thread safety)
static LOG_FILE: Mutex<Option<fs::File>> = Mutex::new(None);

/// Initialize file logging.
///
/// Creates a new log file with timestamp in the logs/ directory.
/// Should be called once at CLI startup.
///
/// # Example
/// ```rust,ignore
/// init_file_logging().expect("Failed to initialize logging");
/// ```
///
/// # Errors
///
/// Returns an error if the logs directory cannot be created or the log file cannot be opened.
#[allow(dead_code)]
pub fn init_file_logging() -> std::io::Result<PathBuf> {
    use std::time::SystemTime;

    let now = SystemTime::now();
    let secs = now.duration_since(std::time::UNIX_EPOCH).unwrap().as_secs();
    let datetime = chrono::DateTime::from_timestamp(secs as i64, 0).unwrap();
    let timestamp = datetime.format("%Y-%m-%d-%H%M%S").to_string();

    let log_dir = PathBuf::from("logs");
    fs::create_dir_all(&log_dir)?;

    let log_file = log_dir.join(format!("ats-checker-{timestamp}.log"));
    let file = OpenOptions::new()
        .create(true)
        .write(true)
        .truncate(true)
        .open(&log_file)?;

    if let Ok(mut handle) = LOG_FILE.lock() {
        *handle = Some(file);
        let _ = writeln!(
            handle.as_mut().unwrap(),
            "=== ATS Checker Log Started at {} ===",
            datetime.format("%Y-%m-%d %H:%M:%S")
        );
    }

    println!("Logging to: {}", log_file.display());
    Ok(log_file)
}

/// Internal function to write to log file.
/// Called by debug macros - do not use directly.
#[allow(dead_code)]
pub fn log_to_file(msg: &str) {
    if let Ok(mut handle) = LOG_FILE.lock() {
        if let Some(ref mut file) = *handle {
            use std::time::SystemTime;
            let now = SystemTime::now();
            let secs = now.duration_since(std::time::UNIX_EPOCH).unwrap().as_secs();
            let datetime = chrono::DateTime::from_timestamp(secs as i64, 0).unwrap();
            let _ = writeln!(file, "[{}] {}", datetime.format("%H:%M:%S"), msg);
            let _ = file.flush();
        }
    }
}
