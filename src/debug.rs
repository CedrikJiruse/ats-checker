//! Debug logging utilities for troubleshooting.
//!
//! All debug output is controlled by the `debug` feature flag.
//! To enable debug output, build with: `cargo build --features debug`

/// Print debug message (stderr) - only when `debug` feature is enabled
#[macro_export]
macro_rules! debug {
    ($($arg:tt)*) => {
        #[cfg(feature = "debug")]
        eprintln!($($arg)*)
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
        eprintln!("[ENTER] {}", $func)
    };
}

/// Debug exit function - only when `debug` feature is enabled
#[macro_export]
macro_rules! debug_exit {
    ($func:expr) => {
        #[cfg(feature = "debug")]
        eprintln!("[EXIT] {}", $func)
    };
}

/// Debug variable dump - only when `debug` feature is enabled
#[macro_export]
macro_rules! debug_var {
    ($name:expr, $val:expr) => {
        #[cfg(feature = "debug")]
        eprintln!("[VAR] {} = {:?}", $name, $val)
    };
}
