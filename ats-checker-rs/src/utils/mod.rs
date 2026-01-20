//! Utility functions module.

mod hash;
mod extract;
mod file;
mod validation;

pub use hash::calculate_file_hash;
pub use extract::extract_text_from_file;

use crate::error::Result;
