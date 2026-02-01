//! Automatic setup for Python `JobSpy` dependencies.
//!
//! This module provides automatic detection and installation of Python
//! and `JobSpy` dependencies required for job scraping.
//!
//! This module now uses a project-local Python virtual environment (.venv)
//! to ensure dependencies are isolated and consistently available.

use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::RwLock;

use crate::error::{AtsError, Result};
use crate::{debug, debug_enter, debug_exit, debug_var};

/// Name of the virtual environment directory
const VENV_DIR: &str = ".venv";
/// Required Python packages
const REQUIRED_PACKAGES: &[&str] = &["python-jobspy", "pandas"];

/// Cache for dependency check results to avoid redundant checks
/// Uses `RwLock` to allow clearing after installation
static DEPENDENCY_CHECK_CACHE: RwLock<Option<DependencyCheck>> = RwLock::new(None);

/// Get the path to the virtual environment's Python executable
fn get_venv_python_path() -> PathBuf {
    debug_enter!("get_venv_python_path");
    let venv_path = Path::new(VENV_DIR);
    #[cfg(windows)]
    let result = venv_path.join("Scripts").join("python.exe");
    #[cfg(not(windows))]
    let result = venv_path.join("bin").join("python");
    debug_var!("venv_python_path", &result);
    debug_exit!("get_venv_python_path");
    result
}

/// Check if the virtual environment exists
fn venv_exists() -> bool {
    debug_enter!("venv_exists");
    let path = get_venv_python_path();
    debug!("venv path: {}, exists: {}", path.display(), path.exists());
    debug_exit!("venv_exists");
    path.exists()
}

/// Create a new virtual environment
fn create_venv(python_exe: &str) -> Result<()> {
    debug_enter!("create_venv");
    debug!("Creating venv with Python: {}", python_exe);
    println!("Creating Python virtual environment in {VENV_DIR}...");

    let output = Command::new(python_exe)
        .args(["-m", "venv", VENV_DIR])
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .output()
        .map_err(|e| {
            debug!("Failed to create venv: {}", e);
            AtsError::ScraperError {
                message: format!("Failed to create virtual environment: {e}"),
                source: Some(Box::new(e)),
            }
        })?;

    debug!("venv creation exit status: {}", output.status);

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        debug!("venv creation stderr: {}", stderr);
        return Err(AtsError::ScraperError {
            message: format!("Failed to create virtual environment: {stderr}"),
            source: None,
        });
    }

    println!("Virtual environment created successfully");
    debug_exit!("create_venv");
    Ok(())
}

/// Install packages in the virtual environment
fn install_packages_in_venv(packages: &[&str]) -> Result<()> {
    debug_enter!("install_packages_in_venv");
    debug!("Packages to install: {:?}", packages);

    let venv_python = get_venv_python_path();
    debug!("venv_python path: {}", venv_python.display());

    // Use the venv Python to run pip as a module (more reliable)
    let python_exe = if venv_python.exists() {
        let exe = venv_python.to_string_lossy().to_string();
        debug!("Using venv Python: {}", exe);
        exe
    } else {
        debug!("venv Python not found at: {}", venv_python.display());
        return Err(AtsError::ScraperError {
            message: "Virtual environment Python not found".to_string(),
            source: None,
        });
    };

    println!(
        "Installing packages in virtual environment: {}",
        packages.join(", ")
    );

    for package in packages {
        print!("  Installing {package}... ");
        std::io::Write::flush(&mut std::io::stdout()).ok();
        debug!("Installing package: {}", package);

        let result = Command::new(&python_exe)
            .args(["-m", "pip", "install", package, "--quiet"])
            .stdout(Stdio::null())
            .stderr(Stdio::piped())
            .output();

        match result {
            Ok(output) => {
                debug!("pip exit status for {}: {}", package, output.status);
                if output.status.success() {
                    println!("✓");
                    debug!("Successfully installed {}", package);
                } else {
                    println!("✗");
                    let stderr = String::from_utf8_lossy(&output.stderr);
                    debug!("pip stderr for {}: {}", package, stderr);
                    eprintln!(
                        "    Error: {}",
                        stderr.lines().next().unwrap_or("Unknown error")
                    );
                    return Err(AtsError::ScraperError {
                        message: format!("Failed to install {package}: {stderr}"),
                        source: None,
                    });
                }
            }
            Err(e) => {
                println!("✗");
                debug!("pip command failed for {}: {}", package, e);
                return Err(AtsError::ScraperError {
                    message: format!("Failed to run pip for {package}: {e}"),
                    source: Some(Box::new(e)),
                });
            }
        }
    }

    println!("All packages installed successfully");
    debug!("All packages installed, clearing cache");

    // Clear cache so next check will see the newly installed packages
    clear_dependency_cache();

    debug_exit!("install_packages_in_venv");
    Ok(())
}

/// Check if a package is installed in the virtual environment
fn check_venv_package(package: &str) -> bool {
    let venv_python = get_venv_python_path();

    if !venv_python.exists() {
        return false;
    }

    // Use -W ignore to suppress numpy warnings on Windows MINGW-W64
    let output = Command::new(&venv_python)
        .args(["-W", "ignore", "-c", &format!("import {package}")])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .output();

    matches!(output, Ok(result) if result.status.success())
}

/// Get the Python executable path to use (venv preferred)
pub fn get_python_exe() -> String {
    // Prefer venv Python if it exists
    let venv_python = get_venv_python_path();
    if venv_python.exists() {
        return venv_python.to_string_lossy().to_string();
    }

    // Fall back to system Python
    find_python().unwrap_or_else(|| "python".to_string())
}

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
///
/// This function uses a virtual environment (.venv) to ensure dependencies
/// are isolated and consistently available. It will automatically create
/// the venv and install packages if needed.
///
/// Results are cached after the first call to avoid redundant checks.
/// Call `clear_dependency_cache()` after installing packages to refresh.
pub fn check_dependencies() -> DependencyCheck {
    // Try to read from cache first
    if let Ok(cache) = DEPENDENCY_CHECK_CACHE.read() {
        if let Some(cached) = cache.as_ref() {
            return cached.clone();
        }
    }

    // Cache miss - perform the check
    let result = perform_dependency_check();

    // Store in cache
    if let Ok(mut cache) = DEPENDENCY_CHECK_CACHE.write() {
        *cache = Some(result.clone());
    }

    result
}

/// Clear the dependency check cache.
/// Call this after installing packages to ensure fresh checks.
pub fn clear_dependency_cache() {
    if let Ok(mut cache) = DEPENDENCY_CHECK_CACHE.write() {
        *cache = None;
    }
}

/// Internal function that performs the actual dependency check.
fn perform_dependency_check() -> DependencyCheck {
    // First, try to find system Python
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

    // Check if venv exists, if not create it
    if !venv_exists() {
        println!("Virtual environment not found. Creating one...");
        if let Err(_e) = create_venv(&python_exe) {
            return DependencyCheck {
                python_available: true,
                python_info: Some(PythonInfo {
                    executable: python_exe.clone(),
                    version: version.clone(),
                    has_jobspy: false,
                    has_pandas: false,
                }),
                missing_deps: vec!["Failed to create venv".to_string()],
                can_auto_install: false,
            };
        }

        // Install packages in the new venv
        if let Err(_e) = install_packages_in_venv(REQUIRED_PACKAGES) {
            return DependencyCheck {
                python_available: true,
                python_info: Some(PythonInfo {
                    executable: get_venv_python_path().to_string_lossy().to_string(),
                    version: version.clone(),
                    has_jobspy: false,
                    has_pandas: false,
                }),
                missing_deps: vec!["Failed to install packages".to_string()],
                can_auto_install: false,
            };
        }
    }

    // Check for required packages in venv
    let has_jobspy = check_venv_package("jobspy");
    let has_pandas = check_venv_package("pandas");

    let mut missing_deps = Vec::new();
    if !has_jobspy {
        missing_deps.push("python-jobspy".to_string());
    }
    if !has_pandas {
        missing_deps.push("pandas".to_string());
    }

    // Get venv Python path
    let venv_python = get_venv_python_path();
    let venv_python_str = venv_python.to_string_lossy().to_string();

    let python_info = PythonInfo {
        executable: venv_python_str,
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
    // On Windows, prefer the 'py' launcher which is more reliable
    #[cfg(windows)]
    let candidates = ["py", "python", "python3"];
    #[cfg(not(windows))]
    let candidates = ["python3", "python", "py"];

    for exe in &candidates {
        if let Ok(output) = Command::new(exe).arg("--version").output() {
            if output.status.success() {
                return Some(exe.to_string());
            }
        }
    }

    // On Windows, try to find Python using the 'where' command
    #[cfg(windows)]
    {
        if let Ok(output) = Command::new("where").arg("python").output() {
            if output.status.success() {
                let paths = String::from_utf8_lossy(&output.stdout);
                for line in paths.lines() {
                    let path = line.trim();
                    if !path.is_empty() && !path.contains("WindowsApps") {
                        // Test if this Python actually works
                        if Command::new(path).arg("--version").output().is_ok() {
                            return Some(path.to_string());
                        }
                    }
                }
            }
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

        // Clear cache so next check will see the newly installed packages
        clear_dependency_cache();

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
/// This function checks for Python and required packages using a virtual
/// environment (.venv). It will automatically create the venv and install
/// packages if needed.
///
/// # Returns
///
/// Returns `Ok(())` if setup is successful or already complete.
///
/// # Errors
///
/// Returns an error if:
/// - Python is not installed
/// - Virtual environment cannot be created
/// - Dependencies cannot be installed automatically
pub fn run_auto_setup() -> Result<()> {
    println!("Checking JobSpy dependencies...");

    let check = check_dependencies();

    if check.is_ready() {
        if let Some(info) = check.python_info {
            println!(
                "✓ Python {} found (using virtual environment)",
                info.version
            );
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

    // Python found but missing packages - venv should have been created by check_dependencies
    // but packages may need installation
    if let Some(info) = check.python_info {
        if !check.missing_deps.is_empty() {
            println!(
                "✓ Python {} found (using virtual environment)",
                info.version
            );
            println!("✗ Missing dependencies: {}", check.missing_deps.join(", "));
            println!();

            // Try auto-install in venv
            println!("Attempting automatic installation in virtual environment...");
            let packages: Vec<&str> = check.missing_deps.iter().map(String::as_str).collect();
            install_packages_in_venv(&packages)?;
        }
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

    #[test]
    fn test_dependency_cache_clears() {
        // First, ensure cache is clear
        clear_dependency_cache();

        // Verify cache is empty
        {
            let cache = DEPENDENCY_CHECK_CACHE.read().unwrap();
            assert!(cache.is_none());
        }

        // Perform a check to populate cache
        let _result = check_dependencies();

        // Verify cache is populated (if Python is available)
        // Note: In CI without Python, this won't populate the cache
        // but the cache clearing logic should still work

        // Clear cache
        clear_dependency_cache();

        // Verify cache is empty after clearing
        {
            let cache = DEPENDENCY_CHECK_CACHE.read().unwrap();
            assert!(cache.is_none());
        }
    }

    #[test]
    fn test_cache_returns_same_result() {
        // Clear cache first
        clear_dependency_cache();

        // Get first result
        let first = check_dependencies();

        // Get second result (should be from cache)
        let second = check_dependencies();

        // Results should be identical
        assert_eq!(first.python_available, second.python_available);
        assert_eq!(first.is_ready(), second.is_ready());
        assert_eq!(first.missing_deps, second.missing_deps);
    }

    #[test]
    fn test_clear_cache_idempotent() {
        // Clear cache multiple times should not panic
        clear_dependency_cache();
        clear_dependency_cache();
        clear_dependency_cache();

        // Verify cache is still clear
        {
            let cache = DEPENDENCY_CHECK_CACHE.read().unwrap();
            assert!(cache.is_none());
        }
    }
}
