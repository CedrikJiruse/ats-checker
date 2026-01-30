//! Automatic setup for Python `JobSpy` dependencies.
//!
//! This module provides automatic detection and installation of Python
//! and `JobSpy` dependencies required for job scraping.

use std::process::{Command, Stdio};

use crate::error::{AtsError, Result};

/// Information about the Python environment.
#[derive(Debug, Clone)]
pub struct PythonInfo {
    /// Python executable path.
    pub executable: String,
    /// Python version string.
    pub version: String,
    /// Whether `JobSpy` is installed.
    pub has_jobspy: bool,
    /// Whether pandas is installed.
    pub has_pandas: bool,
}

/// Result of dependency check.
#[derive(Debug, Clone)]
pub struct DependencyCheck {
    /// Whether Python is available.
    pub python_available: bool,
    /// Python information if available.
    pub python_info: Option<PythonInfo>,
    /// List of missing dependencies.
    pub missing_deps: Vec<String>,
    /// Whether auto-install is possible.
    pub can_auto_install: bool,
}

impl DependencyCheck {
    /// Check if all dependencies are satisfied.
    #[must_use]
    pub fn is_ready(&self) -> bool {
        self.python_available && self.missing_deps.is_empty()
    }

    /// Get a summary of the dependency status.
    #[must_use]
    pub fn summary(&self) -> String {
        if self.is_ready() {
            "All dependencies ready".to_string()
        } else if !self.python_available {
            "Python not found".to_string()
        } else {
            format!("Missing: {}", self.missing_deps.join(", "))
        }
    }
}

/// Check if Python and required dependencies are available.
pub fn check_dependencies() -> DependencyCheck {
    // First, try to find Python
    let Some(python_exe) = find_python() else {
        return DependencyCheck {
            python_available: false,
            python_info: None,
            missing_deps: vec!["Python".to_string()],
            can_auto_install: false,
        };
    };

    // Get Python version
    let Some(version) = get_python_version(&python_exe) else {
        return DependencyCheck {
            python_available: false,
            python_info: None,
            missing_deps: vec!["Python".to_string()],
            can_auto_install: false,
        };
    };

    // Check for required packages
    let has_jobspy = check_python_package(&python_exe, "jobspy");
    let has_pandas = check_python_package(&python_exe, "pandas");

    let mut missing_deps = Vec::new();
    if !has_jobspy {
        missing_deps.push("python-jobspy".to_string());
    }
    if !has_pandas {
        missing_deps.push("pandas".to_string());
    }

    let python_info = PythonInfo {
        executable: python_exe.clone(),
        version,
        has_jobspy,
        has_pandas,
    };

    DependencyCheck {
        python_available: true,
        python_info: Some(python_info),
        can_auto_install: !missing_deps.is_empty(),
        missing_deps,
    }
}

/// Find available Python executable.
fn find_python() -> Option<String> {
    // Try common Python executable names
    let candidates = ["python3", "python", "py"];

    for exe in &candidates {
        if Command::new(exe).arg("--version").output().is_ok() {
            return Some(exe.to_string());
        }
    }

    None
}

/// Get Python version string.
fn get_python_version(exe: &str) -> Option<String> {
    let output = Command::new(exe).arg("--version").output().ok()?;

    if !output.status.success() {
        return None;
    }

    let version = String::from_utf8_lossy(&output.stdout);
    let version = version.trim();

    // Python 3 outputs to stderr for --version
    if version.is_empty() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        Some(stderr.trim().to_string())
    } else {
        Some(version.to_string())
    }
}

/// Check if a Python package is installed.
fn check_python_package(exe: &str, package: &str) -> bool {
    let output = Command::new(exe)
        .args(["-c", &format!("import {package}")])
        .output();

    match output {
        Ok(result) => result.status.success(),
        Err(_) => false,
    }
}

/// Attempt to install missing dependencies automatically.
///
/// # Errors
///
/// Returns an error if installation fails.
pub fn auto_install_deps(python_exe: &str, deps: &[String]) -> Result<()> {
    if deps.is_empty() {
        return Ok(());
    }

    println!("Installing missing dependencies: {}", deps.join(", "));
    println!("This may take a few minutes...");

    // Try to install with pip
    let mut all_success = true;

    for dep in deps {
        print!("  Installing {dep}... ");
        std::io::Write::flush(&mut std::io::stdout()).ok();

        let result = Command::new(python_exe)
            .args(["-m", "pip", "install", dep, "--quiet"])
            .stdout(Stdio::null())
            .stderr(Stdio::piped())
            .output();

        match result {
            Ok(output) => {
                if output.status.success() {
                    println!("✓");
                } else {
                    println!("✗");
                    let stderr = String::from_utf8_lossy(&output.stderr);
                    eprintln!(
                        "    Error: {}",
                        stderr.lines().next().unwrap_or("Unknown error")
                    );
                    all_success = false;
                }
            }
            Err(e) => {
                println!("✗");
                eprintln!("    Failed to run pip: {e}");
                all_success = false;
            }
        }
    }

    if all_success {
        println!("\n✓ All dependencies installed successfully!");
        Ok(())
    } else {
        Err(AtsError::ScraperError {
            message: "Failed to install some dependencies. Please install manually:\n  pip install python-jobspy pandas".to_string(),
            source: None,
        })
    }
}

/// Run automatic setup for `JobSpy` dependencies.
///
/// This function checks for Python and required packages, and attempts
/// to install anything that's missing.
///
/// # Returns
///
/// Returns `Ok(())` if setup is successful or already complete.
///
/// # Errors
///
/// Returns an error if:
/// - Python is not installed
/// - Dependencies cannot be installed automatically
pub fn run_auto_setup() -> Result<()> {
    println!("Checking JobSpy dependencies...");

    let check = check_dependencies();

    if check.is_ready() {
        if let Some(info) = check.python_info {
            println!("✓ Python {} found", info.version);
            println!("✓ JobSpy ready");
        }
        return Ok(());
    }

    // Python not found
    if !check.python_available {
        return Err(AtsError::ScraperError {
            message: "Python is not installed or not in PATH.\n\
                 Please install Python 3.8+ from <https://python.org>\n\
                 After installation, restart this application."
                .to_string(),
            source: None,
        });
    }

    // Python found but missing packages
    if let Some(info) = check.python_info {
        println!("✓ Python {} found", info.version);
        println!("✗ Missing dependencies: {}", check.missing_deps.join(", "));
        println!();

        // Try auto-install
        println!("Attempting automatic installation...");
        auto_install_deps(&info.executable, &check.missing_deps)?;
    }

    Ok(())
}

/// Display dependency status without attempting installation.
pub fn show_dependency_status() {
    println!("\n{}", "-".repeat(60));
    println!("JobSpy Dependencies Status");
    println!("{}", "-".repeat(60));

    let check = check_dependencies();

    if let Some(ref info) = check.python_info {
        println!("  Python: {} ✓", info.version);
        println!(
            "  JobSpy: {}",
            if info.has_jobspy {
                "✓ Installed"
            } else {
                "✗ Missing"
            }
        );
        println!(
            "  Pandas: {}",
            if info.has_pandas {
                "✓ Installed"
            } else {
                "✗ Missing"
            }
        );
    } else {
        println!("  Python: ✗ Not found");
        println!("  JobSpy: ⚠ Cannot check (Python not found)");
        println!("  Pandas: ⚠ Cannot check (Python not found)");
    }

    println!("{}", "-".repeat(60));

    if check.is_ready() {
        return;
    }

    println!("\nTo fix:");
    if check.python_available {
        println!("  Run: pip install python-jobspy pandas");
    } else {
        println!("  1. Install Python 3.8+ from <https://python.org>");
        println!("  2. Make sure Python is added to your PATH");
        println!("  3. Restart this application");
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_find_python() {
        // This should find Python if it's installed
        let python = find_python();
        // We can't assert it's Some because Python might not be in test env
        // but we can assert it doesn't panic
        let _ = python;
    }

    #[test]
    fn test_dependency_check_summary() {
        let check = DependencyCheck {
            python_available: true,
            python_info: Some(PythonInfo {
                executable: "python".to_string(),
                version: "3.9.0".to_string(),
                has_jobspy: false,
                has_pandas: false,
            }),
            missing_deps: vec!["python-jobspy".to_string()],
            can_auto_install: true,
        };

        assert!(!check.is_ready());
        assert_eq!(check.summary(), "Missing: python-jobspy");
    }
}
