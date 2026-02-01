//! Debug logging utilities for troubleshooting.
//!
//! File logging is controlled by the `logging` feature flag.
//! To enable file logging, build with: `cargo build --features logging`
//!
//! Console debug output is controlled by the `debug` feature flag.
//! To enable console debug output, build with: `cargo build --features debug`

/// Log debug message to file - only when `logging` feature is enabled
#[macro_export]
macro_rules! debug {
    ($($arg:tt)*) => {
        #[cfg(feature = "logging")]
        {
            $crate::debug::log_to_file(&format!($($arg)*));
        }
        #[cfg(feature = "debug")]
        {
            eprintln!($($arg)*);
        }
    };
}

/// Log debug message without newline - only when `logging` or `debug` feature is enabled
#[macro_export]
macro_rules! debug_print {
    ($($arg:tt)*) => {
        #[cfg(feature = "logging")]
        {
            $crate::debug::log_to_file(&format!($($arg)*));
        }
        #[cfg(feature = "debug")]
        {
            eprint!($($arg)*);
        }
    };
}

/// Log section header - only when `logging` or `debug` feature is enabled
#[macro_export]
macro_rules! debug_section {
    ($title:expr) => {
        #[cfg(feature = "logging")]
        {
            $crate::debug::log_to_file(&format!("\n▶▶▶ {} ◀◀◀", $title));
        }
        #[cfg(feature = "debug")]
        {
            eprintln!("\n▶▶▶ {} ◀◀◀", $title);
        }
    };
}

/// Log subsection - only when `logging` or `debug` feature is enabled
#[macro_export]
macro_rules! debug_subsection {
    ($title:expr) => {
        #[cfg(feature = "logging")]
        {
            $crate::debug::log_to_file(&format!("  > {}", $title));
        }
        #[cfg(feature = "debug")]
        {
            eprintln!("  > {}", $title);
        }
    };
}

/// Log function entry - only when `logging` or `debug` feature is enabled
#[macro_export]
macro_rules! debug_enter {
    ($func:expr) => {
        #[cfg(feature = "logging")]
        {
            $crate::debug::log_to_file(&format!("[ENTER] {}", $func));
        }
        #[cfg(feature = "debug")]
        {
            eprintln!("[ENTER] {}", $func);
        }
    };
}

/// Log function exit - only when `logging` or `debug` feature is enabled
#[macro_export]
macro_rules! debug_exit {
    ($func:expr) => {
        #[cfg(feature = "logging")]
        {
            $crate::debug::log_to_file(&format!("[EXIT] {}", $func));
        }
        #[cfg(feature = "debug")]
        {
            eprintln!("[EXIT] {}", $func);
        }
    };
}

/// Log variable dump - only when `logging` or `debug` feature is enabled
#[macro_export]
macro_rules! debug_var {
    ($name:expr, $val:expr) => {
        #[cfg(feature = "logging")]
        {
            $crate::debug::log_to_file(&format!("[VAR] {} = {:?}", $name, $val));
        }
        #[cfg(feature = "debug")]
        {
            eprintln!("[VAR] {} = {:?}", $name, $val);
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
