//! Utility functions module.

pub mod extract;
pub mod file;
pub mod hash;
pub mod validation;

pub use extract::extract_text_from_file;
pub use hash::calculate_file_hash;

use crate::error::Result;
