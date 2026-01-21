# ATS Resume Checker - Rust Rewrite Comprehensive Todo List

This document contains a comprehensive list of tasks for rewriting the ATS Resume Checker from Python to Rust. Each item should be checked off as completed.

**Progress Tracking:**
- Total Items: 1,600+
- Completed: ~550 (34%)
- In Progress: 0
- Status: Phase 1-11 Core Implementation Complete - Ready for Testing & Integration

**Completed Phases:**
- ✅ Phase 1: Project Setup & Infrastructure (Items 1-50) - COMPLETE
  - Cargo project initialized with all dependencies
  - Project structure created with all modules
  - Git repository restructured (Rust at root, Python in python-original/)

- ✅ Phase 2: Error Handling & Core Types (Items 51-120) - COMPLETE
  - AtsError enum with 30+ variants implemented
  - Result type aliases defined
  - JobPosting, SearchFilters, SavedSearch types complete

- ✅ Phase 3: Configuration Module (Items 121-220) - COMPLETE
  - Config struct with 40+ fields implemented
  - TOML loading with profile overlay support
  - Path expansion and validation

- ✅ Phase 4: State Management (Items 221-300) - COMPLETE
  - StateManager with TOML persistence
  - Atomic file writes
  - Content hash tracking

- ✅ Phase 5: Utilities Module (Items 301-380) - MOSTLY COMPLETE
  - SHA256 file hashing implemented
  - Text extraction for TXT/MD/TEX files
  - File operations (atomic write, ensure_directory)

- ✅ Phase 6: Scoring Algorithms (Items 381-500) - COMPLETE
  - Resume scoring (completeness, skills_quality, experience_quality, impact)
  - Job scoring (completeness, clarity, compensation_transparency, link_quality)
  - Match scoring (keyword_overlap, skills_overlap, role_alignment)
  - Weight loading and normalization
  - All utility functions implemented with tests

- ✅ Phase 7: Agent System (Items 501-650) - COMPLETE
  - ✅ Agent trait defined with async/await support
  - ✅ AgentConfig with builder pattern
  - ✅ GeminiAgent implementation with retry logic
  - ✅ AgentRegistry for managing multiple agents
  - ✅ JSON validation and fence stripping
  - 🚧 OpenAI/Claude/Llama agents (future work)

- ✅ Phase 8: Gemini API Client (Items 651-700) - COMPLETE
  - ✅ Full HTTP client implementation with reqwest
  - ✅ GenerationConfig support (temperature, top_p, top_k, max_tokens)
  - ✅ Proper error handling (auth, rate limit, timeout, response errors)
  - ✅ JSON generation with fence stripping
  - ✅ Builder pattern for configuration
  - ✅ Environment variable support

- ✅ Phase 9: Output Generation (Items 701-800) - COMPLETE
  - ✅ InputHandler for loading resumes and job descriptions
  - ✅ Support for multiple file formats (TXT, PDF, DOCX, MD, TEX)
  - ✅ New resume detection using state hashes
  - ✅ OutputGenerator with TOML/JSON/TXT formatting
  - ✅ Output directory creation with pattern substitution
  - ✅ Manifest and score summary file generation

- ✅ Phase 10: Resume Processor Pipeline (Items 801-900) - COMPLETE
  - ✅ ResumeProcessor main structure
  - ✅ Full processing pipeline (load → enhance → score → iterate → output)
  - ✅ Iteration strategies (best_of, first_hit, patience)
  - ✅ Integration with all core components
  - ✅ Prompt templates for AI interactions
  - ✅ State management integration
  - ✅ Batch processing support

- ✅ Phase 11: CLI Implementation (Items 1051-1150) - COMPLETE
  - ✅ CLI argument parsing with clap
  - ✅ Subcommands: score-resume, score-match, rank-jobs
  - ✅ Interactive menu system with multiple options
  - ✅ Command handlers with formatted output
  - ✅ Verbose and quiet logging modes
  - ✅ Resume/job file viewing
  - ✅ Configuration and state viewing
  - ✅ Comprehensive error handling

**Next Steps:**
1. Add comprehensive integration tests
2. Implement job scraper integration with JobSpy
3. Add remaining utility functions (PDF/DOCX extraction improvements)
4. Add OpenAI/Claude/Llama agent implementations
5. Add prompt template system for customizable prompts

---

## Phase 1: Project Setup & Infrastructure (Items 1-50)

### 1.1 Cargo Project Initialization (1-10) ✅ COMPLETE
- [x] 1. Create new Rust project with `cargo new ats-checker-rs --lib`
- [x] 2. Create binary crate for CLI in `src/bin/main.rs`
- [x] 3. Configure `Cargo.toml` with project metadata (name, version, authors, license)
- [x] 4. Add `[lib]` section to Cargo.toml
- [x] 5. Add `[[bin]]` section for CLI binary
- [x] 6. Configure edition = "2021"
- [x] 7. Set up workspace if needed for multiple crates (decided single crate)
- [x] 8. Add `.gitignore` for Rust project (target/, Cargo.lock for lib)
- [ ] 9. Create `rust-toolchain.toml` specifying stable toolchain
- [ ] 10. Set up `clippy.toml` with lint configurations

### 1.2 Core Dependencies Setup (11-30) ✅ COMPLETE
- [x] 11. Add `serde` dependency with derive feature
- [x] 12. Add `serde_json` for JSON serialization
- [x] 13. Add `toml` crate for TOML parsing
- [x] 14. Add `tokio` runtime with full features for async
- [x] 15. Add `reqwest` for HTTP client (API calls)
- [x] 16. Add `clap` with derive feature for CLI argument parsing
- [x] 17. Add `thiserror` for error type definitions
- [x] 18. Add `anyhow` for error propagation in binary
- [x] 19. Add `log` facade for logging
- [x] 20. Add `env_logger` for logging implementation (plus tracing)
- [x] 21. Add `sha2` crate for SHA256 hashing
- [x] 22. Add `pdf-extract` or `lopdf` for PDF text extraction
- [x] 23. Add `regex` crate for text pattern matching
- [x] 24. Add `chrono` for date/time handling
- [x] 25. Add `uuid` for unique identifier generation
- [x] 26. Add `tempfile` for temporary file operations
- [x] 27. Add `walkdir` for directory traversal
- [x] 28. Add `dialoguer` for interactive CLI prompts
- [x] 29. Add `indicatif` for progress bars
- [x] 30. Add `console` for terminal colors

### 1.3 Development Dependencies (31-40) ✅ COMPLETE
- [x] 31. Add `pretty_assertions` for test assertions
- [x] 32. Add `mockall` for mocking in tests
- [x] 33. Add `tempfile` for test fixtures
- [x] 34. Add `tokio-test` for async test utilities
- [x] 35. Add `criterion` for benchmarking
- [x] 36. Add `proptest` for property-based testing
- [x] 37. Add `rstest` for parameterized tests
- [x] 38. Add `wiremock` for HTTP mocking
- [x] 39. Add `test-case` for test case generation
- [x] 40. Add `insta` for snapshot testing

### 1.4 Project Structure Setup (41-50) ✅ COMPLETE
- [x] 41. Create `src/lib.rs` with module declarations
- [x] 42. Create `src/config/mod.rs` module
- [x] 43. Create `src/state/mod.rs` module
- [x] 44. Create `src/utils/mod.rs` module
- [x] 45. Create `src/scoring/mod.rs` module
- [x] 46. Create `src/agents/mod.rs` module
- [x] 47. Create `src/scraper/mod.rs` module
- [x] 48. Create `src/output/mod.rs` module
- [x] 49. Create `src/input/mod.rs` module
- [x] 50. Create `src/error.rs` for error types

---

## Phase 2: Error Handling & Core Types (Items 51-120)

### 2.1 Error Type Definitions (51-75)
- [ ] 51. Define `AtsError` enum as main error type
- [ ] 52. Add `ConfigError` variant for configuration errors
- [ ] 53. Add `IoError` variant wrapping `std::io::Error`
- [ ] 54. Add `ParseError` variant for parsing failures
- [ ] 55. Add `TomlError` variant for TOML parsing errors
- [ ] 56. Add `JsonError` variant for JSON parsing errors
- [ ] 57. Add `ValidationError` variant for schema validation
- [ ] 58. Add `ApiError` variant for external API failures
- [ ] 59. Add `GeminiError` variant for Gemini API errors
- [ ] 60. Add `OpenAIError` variant for OpenAI API errors
- [ ] 61. Add `AnthropicError` variant for Anthropic API errors
- [ ] 62. Add `ScraperError` variant for job scraping errors
- [ ] 63. Add `ScoringError` variant for scoring calculation errors
- [ ] 64. Add `StateError` variant for state management errors
- [ ] 65. Add `OutputError` variant for output generation errors
- [ ] 66. Add `InputError` variant for input handling errors
- [ ] 67. Add `PdfError` variant for PDF extraction errors
- [ ] 68. Add `OcrError` variant for OCR processing errors
- [ ] 69. Add `HashError` variant for file hashing errors
- [ ] 70. Add `NetworkError` variant for network failures
- [ ] 71. Add `TimeoutError` variant for operation timeouts
- [ ] 72. Add `RateLimitError` variant for API rate limiting
- [ ] 73. Implement `std::error::Error` for `AtsError`
- [ ] 74. Implement `std::fmt::Display` for `AtsError`
- [ ] 75. Implement `From` conversions for wrapped error types

### 2.2 Result Type Aliases (76-80)
- [ ] 76. Define `Result<T> = std::result::Result<T, AtsError>` alias
- [ ] 77. Define `ConfigResult<T>` type alias
- [ ] 78. Define `ScoringResult<T>` type alias
- [ ] 79. Define `ApiResult<T>` type alias
- [ ] 80. Define `IoResult<T>` type alias

### 2.3 Core Data Structures - JobPosting (81-95)
- [ ] 81. Define `JobPosting` struct with all fields
- [ ] 82. Add `title: String` field
- [ ] 83. Add `company: String` field
- [ ] 84. Add `location: String` field
- [ ] 85. Add `description: String` field
- [ ] 86. Add `url: String` field
- [ ] 87. Add `source: String` field
- [ ] 88. Add `posted_date: Option<String>` field
- [ ] 89. Add `salary: Option<String>` field
- [ ] 90. Add `job_type: Option<String>` field
- [ ] 91. Add `remote: Option<bool>` field
- [ ] 92. Add `experience_level: Option<String>` field
- [ ] 93. Add `scraped_at: String` field with default
- [ ] 94. Derive `Serialize`, `Deserialize` for JobPosting
- [ ] 95. Derive `Clone`, `Debug`, `PartialEq` for JobPosting

### 2.4 Core Data Structures - SearchFilters (96-110)
- [ ] 96. Define `SearchFilters` struct
- [ ] 97. Add `keywords: Option<String>` field
- [ ] 98. Add `location: Option<String>` field
- [ ] 99. Add `job_type: Option<Vec<String>>` field
- [ ] 100. Add `remote_only: bool` field with default false
- [ ] 101. Add `experience_level: Option<Vec<String>>` field
- [ ] 102. Add `salary_min: Option<i32>` field
- [ ] 103. Add `date_posted: Option<String>` field
- [ ] 104. Derive `Serialize`, `Deserialize` for SearchFilters
- [ ] 105. Derive `Clone`, `Debug`, `Default` for SearchFilters
- [ ] 106. Implement `SearchFilters::new()` constructor
- [ ] 107. Implement `SearchFilters::with_keywords()` builder method
- [ ] 108. Implement `SearchFilters::with_location()` builder method
- [ ] 109. Implement `SearchFilters::with_remote_only()` builder method
- [ ] 110. Implement builder pattern for SearchFilters

### 2.5 Core Data Structures - SavedSearch (111-120)
- [ ] 111. Define `SavedSearch` struct
- [ ] 112. Add `name: String` field
- [ ] 113. Add `filters: SearchFilters` field
- [ ] 114. Add `sources: Vec<String>` field
- [ ] 115. Add `max_results: i32` field with default 50
- [ ] 116. Add `created_at: String` field
- [ ] 117. Add `last_run: Option<String>` field
- [ ] 118. Derive `Serialize`, `Deserialize` for SavedSearch
- [ ] 119. Derive `Clone`, `Debug` for SavedSearch
- [ ] 120. Implement `SavedSearch::new()` constructor

---

## Phase 3: Configuration Module (Items 121-220)

### 3.1 Config Struct Definition (121-145)
- [ ] 121. Create `src/config/mod.rs` file
- [ ] 122. Define main `Config` struct
- [ ] 123. Add `input_resumes_folder: PathBuf` field
- [ ] 124. Add `job_descriptions_folder: PathBuf` field
- [ ] 125. Add `output_folder: PathBuf` field
- [ ] 126. Add `state_file: PathBuf` field
- [ ] 127. Add `scoring_weights_file: PathBuf` field
- [ ] 128. Add `saved_searches_file: PathBuf` field
- [ ] 129. Add `job_search_results_folder: PathBuf` field
- [ ] 130. Add `tesseract_cmd: Option<String>` field
- [ ] 131. Add `gemini_api_key_env: String` field
- [ ] 132. Add `default_model_name: String` field
- [ ] 133. Add `default_temperature: f64` field
- [ ] 134. Add `default_top_p: f64` field
- [ ] 135. Add `default_top_k: i32` field
- [ ] 136. Add `default_max_output_tokens: i32` field
- [ ] 137. Add `num_versions_per_job: i32` field
- [ ] 138. Add `iterate_until_score_reached: bool` field
- [ ] 139. Add `target_score: f64` field
- [ ] 140. Add `max_iterations: i32` field
- [ ] 141. Add `iteration_strategy: String` field
- [ ] 142. Add `max_regressions: i32` field
- [ ] 143. Add `max_concurrent_requests: i32` field
- [ ] 144. Add `score_cache_enabled: bool` field
- [ ] 145. Add `structured_output_format: String` field

### 3.2 Config Additional Fields (146-165)
- [ ] 146. Add `schema_validation_enabled: bool` field
- [ ] 147. Add `resume_schema_path: PathBuf` field
- [ ] 148. Add `recommendations_enabled: bool` field
- [ ] 149. Add `recommendations_max_items: i32` field
- [ ] 150. Add `output_subdir_pattern: String` field
- [ ] 151. Add `ai_agents: HashMap<String, AgentConfig>` field
- [ ] 152. Add `job_portals: HashMap<String, PortalConfig>` field
- [ ] 153. Add `job_search_default_sources: Vec<String>` field
- [ ] 154. Add `job_search_default_max_results: i32` field
- [ ] 155. Add `job_search_default_location: Option<String>` field
- [ ] 156. Add `job_search_default_remote_only: bool` field
- [ ] 157. Add `job_search_default_date_posted: Option<String>` field
- [ ] 158. Add `job_search_default_job_type: Option<Vec<String>>` field
- [ ] 159. Add `profile_file: Option<PathBuf>` field
- [ ] 160. Derive `Serialize`, `Deserialize` for Config
- [ ] 161. Derive `Clone`, `Debug` for Config
- [ ] 162. Implement `Default` for Config
- [ ] 163. Add `#[serde(default)]` attributes where needed
- [ ] 164. Add `#[serde(rename = "...")]` for TOML field names
- [ ] 165. Add `#[serde(skip_serializing_if = "Option::is_none")]` where needed

### 3.3 AgentConfig Struct (166-180)
- [ ] 166. Define `AgentConfig` struct in config module
- [ ] 167. Add `name: String` field
- [ ] 168. Add `provider: String` field with default "gemini"
- [ ] 169. Add `role: String` field with default "generic"
- [ ] 170. Add `model_name: String` field
- [ ] 171. Add `temperature: f64` field
- [ ] 172. Add `top_p: f64` field
- [ ] 173. Add `top_k: i32` field
- [ ] 174. Add `max_output_tokens: i32` field
- [ ] 175. Add `max_retries: i32` field
- [ ] 176. Add `retry_on_empty: bool` field
- [ ] 177. Add `require_json: bool` field
- [ ] 178. Add `extras: HashMap<String, Value>` field
- [ ] 179. Derive all necessary traits for AgentConfig
- [ ] 180. Implement `Default` for AgentConfig

### 3.4 PortalConfig Struct (181-190)
- [ ] 181. Define `PortalConfig` struct
- [ ] 182. Add `enabled: bool` field
- [ ] 183. Add `default_location: Option<String>` field
- [ ] 184. Add `default_country: Option<String>` field
- [ ] 185. Add `default_max_results: Option<i32>` field
- [ ] 186. Add `default_date_posted: Option<String>` field
- [ ] 187. Derive traits for PortalConfig
- [ ] 188. Implement `Default` for PortalConfig
- [ ] 189. Add serde attributes for optional fields
- [ ] 190. Add validation for PortalConfig fields

### 3.5 Config Loading Functions (191-210)
- [ ] 191. Implement `load_config(path: &Path) -> Result<Config>`
- [ ] 192. Implement TOML file reading in load_config
- [ ] 193. Implement path expansion (relative to absolute)
- [ ] 194. Implement `expand_path()` helper function
- [ ] 195. Implement environment variable substitution in paths
- [ ] 196. Implement profile overlay loading
- [ ] 197. Implement `load_profile(path: &Path) -> Result<Config>`
- [ ] 198. Implement config merging (profile + main config)
- [ ] 199. Implement `merge_configs(base: Config, overlay: Config) -> Config`
- [ ] 200. Implement default config creation
- [ ] 201. Implement `Config::default_paths()` for default path values
- [ ] 202. Implement config validation after loading
- [ ] 203. Implement `validate_config(config: &Config) -> Result<()>`
- [ ] 204. Validate required directories exist or can be created
- [ ] 205. Validate API key environment variables are set
- [ ] 206. Validate scoring weights file exists
- [ ] 207. Validate iteration strategy is valid enum value
- [ ] 208. Validate numeric ranges (temperature 0-2, etc.)
- [ ] 209. Implement `Config::ensure_directories()` to create missing dirs
- [ ] 210. Add logging for config loading process

### 3.6 Config Serialization (211-220)
- [ ] 211. Implement `Config::to_toml_string() -> Result<String>`
- [ ] 212. Implement `Config::save_to_file(path: &Path) -> Result<()>`
- [ ] 213. Implement atomic write pattern for config saving
- [ ] 214. Implement config backup before overwrite
- [ ] 215. Add JSON config loading for backward compatibility
- [ ] 216. Implement `load_legacy_json_config(path: &Path) -> Result<Config>`
- [ ] 217. Implement auto-migration from JSON to TOML
- [ ] 218. Add deprecation warnings for JSON configs
- [ ] 219. Implement `Config::reload()` method
- [ ] 220. Add config file watcher support (optional)

---

## Phase 4: State Management Module (Items 221-300)

### 4.1 StateManager Struct (221-240)
- [ ] 221. Create `src/state/mod.rs` file
- [ ] 222. Define `StateManager` struct
- [ ] 223. Add `state_filepath: PathBuf` field
- [ ] 224. Add `state: HashMap<String, ResumeState>` field
- [ ] 225. Define `ResumeState` struct with `output_path: String`
- [ ] 226. Derive traits for ResumeState
- [ ] 227. Implement `StateManager::new(path: PathBuf) -> Result<Self>`
- [ ] 228. Load state from file in constructor
- [ ] 229. Create empty state if file doesn't exist
- [ ] 230. Add error handling for corrupted state files
- [ ] 231. Implement state file locking (prevent concurrent writes)
- [ ] 232. Add state file backup on load
- [ ] 233. Implement `StateManager::get_resume_state(&self, hash: &str) -> Option<&ResumeState>`
- [ ] 234. Implement `StateManager::update_resume_state(&mut self, hash: &str, output_path: &str) -> Result<()>`
- [ ] 235. Implement `StateManager::is_processed(&self, hash: &str) -> bool`
- [ ] 236. Implement `StateManager::remove_state(&mut self, hash: &str) -> Result<()>`
- [ ] 237. Implement `StateManager::clear_all(&mut self) -> Result<()>`
- [ ] 238. Implement `StateManager::list_all_hashes(&self) -> Vec<&str>`
- [ ] 239. Implement `StateManager::count(&self) -> usize`
- [ ] 240. Add logging for state operations

### 4.2 State Persistence - TOML (241-260)
- [ ] 241. Implement `_load_state(&self) -> Result<HashMap<String, ResumeState>>`
- [ ] 242. Implement TOML parsing for state file
- [ ] 243. Handle `[resumes.<hash>]` TOML table structure
- [ ] 244. Implement `_read_toml_state(path: &Path) -> Result<HashMap<...>>`
- [ ] 245. Add validation for loaded state structure
- [ ] 246. Implement `_save_state(&self) -> Result<()>`
- [ ] 247. Implement atomic write pattern (write to temp, rename)
- [ ] 248. Implement `_write_toml_state(path: &Path, state: &HashMap<...>) -> Result<()>`
- [ ] 249. Generate proper TOML structure for nested tables
- [ ] 250. Handle special characters in hash keys
- [ ] 251. Add file permissions handling (Unix)
- [ ] 252. Implement state file rotation (keep N backups)
- [ ] 253. Add compression support for large state files (optional)
- [ ] 254. Implement state file integrity check (checksum)
- [ ] 255. Add recovery from corrupted state files
- [ ] 256. Implement `StateManager::compact()` to remove orphan entries
- [ ] 257. Add timestamp to state entries for cleanup
- [ ] 258. Implement state file migration between versions
- [ ] 259. Add state export to JSON format
- [ ] 260. Add state import from JSON format

### 4.3 Legacy JSON Migration (261-275)
- [ ] 261. Implement `_infer_legacy_json_path(&self) -> Option<PathBuf>`
- [ ] 262. Check for `.json` file with same basename as TOML
- [ ] 263. Check for default `processed_resumes_state.json` path
- [ ] 264. Implement `_read_legacy_json_state(path: &Path) -> Result<HashMap<...>>`
- [ ] 265. Parse legacy JSON structure `{"<hash>": {"output_path": "..."}}`
- [ ] 266. Validate and normalize legacy data
- [ ] 267. Handle malformed legacy entries gracefully
- [ ] 268. Implement automatic migration on first load
- [ ] 269. Save migrated state to TOML immediately
- [ ] 270. Log migration success/failure
- [ ] 271. Optionally rename/archive legacy JSON after migration
- [ ] 272. Add migration status tracking
- [ ] 273. Handle partial migration failures
- [ ] 274. Add rollback support for failed migrations
- [ ] 275. Write migration report file

### 4.4 State Manager Tests (276-300)
- [ ] 276. Create `src/state/tests.rs` module
- [ ] 277. Test `StateManager::new()` with non-existent file
- [ ] 278. Test `StateManager::new()` with existing valid TOML
- [ ] 279. Test `StateManager::new()` with corrupted file
- [ ] 280. Test `StateManager::get_resume_state()` for existing hash
- [ ] 281. Test `StateManager::get_resume_state()` for non-existent hash
- [ ] 282. Test `StateManager::update_resume_state()` new entry
- [ ] 283. Test `StateManager::update_resume_state()` update existing
- [ ] 284. Test `StateManager::is_processed()` true case
- [ ] 285. Test `StateManager::is_processed()` false case
- [ ] 286. Test state persistence across manager instances
- [ ] 287. Test atomic write (simulate crash during write)
- [ ] 288. Test legacy JSON migration
- [ ] 289. Test migration with malformed JSON
- [ ] 290. Test concurrent access (if applicable)
- [ ] 291. Test `remove_state()` functionality
- [ ] 292. Test `clear_all()` functionality
- [ ] 293. Test `list_all_hashes()` functionality
- [ ] 294. Test state file backup creation
- [ ] 295. Test state file recovery
- [ ] 296. Test with special characters in hashes
- [ ] 297. Test with very long output paths
- [ ] 298. Test with Unicode in paths
- [ ] 299. Test empty state handling
- [ ] 300. Add benchmark for large state files

---

## Phase 5: Utilities Module (Items 301-380)

### 5.1 File Hashing (301-320)
- [ ] 301. Create `src/utils/mod.rs` file
- [ ] 302. Create `src/utils/hash.rs` submodule
- [ ] 303. Implement `calculate_file_hash(path: &Path) -> Result<String>`
- [ ] 304. Use SHA256 algorithm from `sha2` crate
- [ ] 305. Read file in chunks for memory efficiency
- [ ] 306. Handle large files (streaming hash)
- [ ] 307. Return lowercase hex string
- [ ] 308. Handle file not found error
- [ ] 309. Handle permission denied error
- [ ] 310. Handle empty file edge case
- [ ] 311. Implement `calculate_string_hash(content: &str) -> String`
- [ ] 312. Implement `calculate_bytes_hash(bytes: &[u8]) -> String`
- [ ] 313. Add hash verification function
- [ ] 314. Implement `verify_file_hash(path: &Path, expected: &str) -> Result<bool>`
- [ ] 315. Add caching for repeated hash calculations
- [ ] 316. Implement hash cache with LRU eviction
- [ ] 317. Add parallel hashing for multiple files
- [ ] 318. Test hash calculation correctness
- [ ] 319. Test hash consistency across runs
- [ ] 320. Benchmark hash calculation performance

### 5.2 Text Extraction (321-350)
- [ ] 321. Create `src/utils/extract.rs` submodule
- [ ] 322. Implement `extract_text_from_file(path: &Path) -> Result<String>`
- [ ] 323. Detect file type by extension
- [ ] 324. Implement `extract_text_from_txt(path: &Path) -> Result<String>`
- [ ] 325. Handle various text encodings (UTF-8, Latin-1, etc.)
- [ ] 326. Implement `extract_text_from_pdf(path: &Path) -> Result<String>`
- [ ] 327. Use `pdf-extract` or `lopdf` crate for PDF extraction
- [ ] 328. Handle encrypted PDFs gracefully
- [ ] 329. Handle scanned PDFs (return empty or trigger OCR)
- [ ] 330. Implement `extract_text_from_docx(path: &Path) -> Result<String>`
- [ ] 331. Use `docx-rs` or similar crate
- [ ] 332. Extract text from all document parts
- [ ] 333. Handle embedded images in DOCX
- [ ] 334. Implement `extract_text_from_md(path: &Path) -> Result<String>`
- [ ] 335. Strip markdown formatting (optional)
- [ ] 336. Implement `extract_text_from_tex(path: &Path) -> Result<String>`
- [ ] 337. Strip LaTeX commands (basic)
- [ ] 338. Implement OCR wrapper for images
- [ ] 339. Implement `extract_text_from_image(path: &Path) -> Result<String>`
- [ ] 340. Call Tesseract OCR binary
- [ ] 341. Handle Tesseract not installed error
- [ ] 342. Support configurable Tesseract path
- [ ] 343. Support multiple image formats (PNG, JPG, TIFF)
- [ ] 344. Add language parameter for OCR
- [ ] 345. Implement text normalization
- [ ] 346. Remove excessive whitespace
- [ ] 347. Normalize line endings
- [ ] 348. Handle special characters
- [ ] 349. Test text extraction for each format
- [ ] 350. Benchmark extraction performance

### 5.3 File Operations (351-370)
- [ ] 351. Create `src/utils/file.rs` submodule
- [ ] 352. Implement `ensure_directory(path: &Path) -> Result<()>`
- [ ] 353. Implement `atomic_write(path: &Path, content: &str) -> Result<()>`
- [ ] 354. Write to temp file then rename
- [ ] 355. Handle cross-filesystem moves
- [ ] 356. Implement `safe_delete(path: &Path) -> Result<()>`
- [ ] 357. Move to trash instead of permanent delete (optional)
- [ ] 358. Implement `copy_file(src: &Path, dst: &Path) -> Result<()>`
- [ ] 359. Implement `move_file(src: &Path, dst: &Path) -> Result<()>`
- [ ] 360. Implement `list_files_with_extension(dir: &Path, ext: &str) -> Result<Vec<PathBuf>>`
- [ ] 361. Implement `find_files_recursive(dir: &Path, pattern: &str) -> Result<Vec<PathBuf>>`
- [ ] 362. Use `walkdir` for recursive traversal
- [ ] 363. Support glob patterns
- [ ] 364. Implement `get_file_size(path: &Path) -> Result<u64>`
- [ ] 365. Implement `get_file_modified_time(path: &Path) -> Result<SystemTime>`
- [ ] 366. Implement path sanitization for output files
- [ ] 367. Replace invalid characters in filenames
- [ ] 368. Handle path length limits (Windows)
- [ ] 369. Test all file operations
- [ ] 370. Add logging for file operations

### 5.4 Validation Helpers (371-380)
- [ ] 371. Create `src/utils/validation.rs` submodule
- [ ] 372. Implement `is_valid_email(s: &str) -> bool`
- [ ] 373. Implement `is_valid_url(s: &str) -> bool`
- [ ] 374. Implement `is_valid_phone(s: &str) -> bool`
- [ ] 375. Implement `sanitize_string(s: &str) -> String`
- [ ] 376. Remove control characters
- [ ] 377. Normalize Unicode
- [ ] 378. Implement `truncate_string(s: &str, max_len: usize) -> String`
- [ ] 379. Handle UTF-8 boundary correctly
- [ ] 380. Test all validation helpers

---

## Phase 6: Scoring Module (Items 381-500)

### 6.1 Score Types (381-400)
- [ ] 381. Create `src/scoring/mod.rs` file
- [ ] 382. Define `ScoreReport` struct
- [ ] 383. Add `total: f64` field
- [ ] 384. Add `categories: Vec<CategoryScore>` field
- [ ] 385. Define `CategoryScore` struct
- [ ] 386. Add `name: String` field to CategoryScore
- [ ] 387. Add `score: f64` field to CategoryScore
- [ ] 388. Add `weight: f64` field to CategoryScore
- [ ] 389. Add `details: Option<CategoryDetails>` field
- [ ] 390. Define `CategoryDetails` enum
- [ ] 391. Add `KeywordOverlap` variant with matched/missing lists
- [ ] 392. Add `SkillAlignment` variant with skill details
- [ ] 393. Add `Generic` variant for other details
- [ ] 394. Derive `Serialize`, `Deserialize` for all score types
- [ ] 395. Derive `Clone`, `Debug` for all score types
- [ ] 396. Implement `ScoreReport::as_dict() -> HashMap<String, Value>`
- [ ] 397. Implement `ScoreReport::from_dict(map: HashMap<...>) -> Result<Self>`
- [ ] 398. Implement `Display` for ScoreReport (formatted output)
- [ ] 399. Add `ScoreReport::summary() -> String` method
- [ ] 400. Add score validation (0-100 range)

### 6.2 Scoring Weights (401-420)
- [ ] 401. Create `src/scoring/weights.rs` submodule
- [ ] 402. Define `ScoringWeights` struct
- [ ] 403. Add `resume_weight: f64` field
- [ ] 404. Add `match_weight: f64` field
- [ ] 405. Add `job_weight: f64` field
- [ ] 406. Add `resume_categories: Vec<CategoryWeight>` field
- [ ] 407. Add `match_categories: Vec<CategoryWeight>` field
- [ ] 408. Add `job_categories: Vec<CategoryWeight>` field
- [ ] 409. Define `CategoryWeight` struct with name and weight
- [ ] 410. Implement `ScoringWeights::load_from_toml(path: &Path) -> Result<Self>`
- [ ] 411. Parse scoring_weights.toml format
- [ ] 412. Handle missing categories with defaults
- [ ] 413. Validate weights sum correctly
- [ ] 414. Implement `ScoringWeights::default() -> Self`
- [ ] 415. Add weight normalization function
- [ ] 416. Implement `normalize_weights(weights: &mut [CategoryWeight])`
- [ ] 417. Add weight override support
- [ ] 418. Test weights loading from TOML
- [ ] 419. Test weight normalization
- [ ] 420. Test default weights

### 6.3 Resume Scoring (421-450)
- [ ] 421. Create `src/scoring/resume.rs` submodule
- [ ] 422. Implement `score_resume(resume: &Value, weights_path: &Path) -> Result<ScoreReport>`
- [ ] 423. Extract resume sections from JSON/TOML structure
- [ ] 424. Score contact information completeness
- [ ] 425. Score summary/objective presence and quality
- [ ] 426. Score experience section
- [ ] 427. Count number of experience entries
- [ ] 428. Evaluate bullet point quality
- [ ] 429. Check for quantifiable achievements
- [ ] 430. Check for action verbs
- [ ] 431. Score education section
- [ ] 432. Check for degree information
- [ ] 433. Check for GPA (optional)
- [ ] 434. Score skills section
- [ ] 435. Count technical skills
- [ ] 436. Categorize skills (languages, frameworks, tools)
- [ ] 437. Score certifications section
- [ ] 438. Score projects section
- [ ] 439. Score publications section
- [ ] 440. Calculate section length scores
- [ ] 441. Penalize too short or too long sections
- [ ] 442. Score formatting consistency
- [ ] 443. Check date format consistency
- [ ] 444. Calculate overall resume score
- [ ] 445. Weight and combine category scores
- [ ] 446. Add detailed breakdown to report
- [ ] 447. Add improvement suggestions based on scores
- [ ] 448. Test resume scoring with sample resumes
- [ ] 449. Test edge cases (empty sections, missing fields)
- [ ] 450. Benchmark scoring performance

### 6.4 Job Scoring (451-470)
- [ ] 451. Create `src/scoring/job.rs` submodule
- [ ] 452. Implement `score_job(job: &JobPosting, weights_path: &Path) -> Result<ScoreReport>`
- [ ] 453. Score job description length
- [ ] 454. Score job title clarity
- [ ] 455. Score company information presence
- [ ] 456. Score location information
- [ ] 457. Score salary information presence
- [ ] 458. Score requirements clarity
- [ ] 459. Extract and count required skills
- [ ] 460. Score responsibilities clarity
- [ ] 461. Score benefits/perks information
- [ ] 462. Score job type information
- [ ] 463. Score experience level clarity
- [ ] 464. Check for red flags (vague descriptions)
- [ ] 465. Calculate keyword density
- [ ] 466. Score URL validity
- [ ] 467. Calculate overall job score
- [ ] 468. Test job scoring with sample jobs
- [ ] 469. Test edge cases (minimal job info)
- [ ] 470. Add job quality recommendations

### 6.5 Match Scoring (471-495)
- [ ] 471. Create `src/scoring/match.rs` submodule
- [ ] 472. Implement `score_match(resume: &Value, job: &Value, weights_path: &Path) -> Result<ScoreReport>`
- [ ] 473. Extract keywords from job description
- [ ] 474. Implement keyword extraction algorithm
- [ ] 475. Use TF-IDF or similar for keyword importance
- [ ] 476. Extract skills from resume
- [ ] 477. Calculate keyword overlap percentage
- [ ] 478. Identify matched keywords
- [ ] 479. Identify missing keywords
- [ ] 480. Score title/role alignment
- [ ] 481. Compare job title with resume titles
- [ ] 482. Score experience level alignment
- [ ] 483. Compare required vs actual experience years
- [ ] 484. Score skills alignment
- [ ] 485. Match technical skills
- [ ] 486. Match soft skills
- [ ] 487. Score location alignment
- [ ] 488. Check remote compatibility
- [ ] 489. Score education requirements match
- [ ] 490. Score industry alignment
- [ ] 491. Calculate overall match score
- [ ] 492. Generate match improvement suggestions
- [ ] 493. Add sample matched/missing keywords to report
- [ ] 494. Test match scoring
- [ ] 495. Test with various resume-job combinations

### 6.6 Iteration Score (496-500)
- [ ] 496. Implement `compute_iteration_score(resume_report: &ScoreReport, match_report: &ScoreReport, weights_path: &Path) -> Result<(f64, HashMap<String, Value>)>`
- [ ] 497. Combine resume and match scores with weights
- [ ] 498. Return combined score and breakdown details
- [ ] 499. Test iteration score calculation
- [ ] 500. Verify score combination logic

---

## Phase 7: Agent/LLM Module (Items 501-600)

### 7.1 Agent Traits (501-520)
- [ ] 501. Create `src/agents/mod.rs` file
- [ ] 502. Define `Agent` trait
- [ ] 503. Add `fn generate_text(&self, prompt: &str) -> Result<String>` method
- [ ] 504. Add `fn generate_json(&self, prompt: &str) -> Result<Value>` method
- [ ] 505. Add `fn config(&self) -> &AgentConfig` method
- [ ] 506. Make Agent trait object-safe
- [ ] 507. Define `AgentError` enum
- [ ] 508. Add `ConfigError` variant
- [ ] 509. Add `ProviderError` variant
- [ ] 510. Add `ResponseError` variant
- [ ] 511. Add `RateLimitError` variant
- [ ] 512. Add `TimeoutError` variant
- [ ] 513. Implement error conversions
- [ ] 514. Define `AgentConfig` struct (if not in config module)
- [ ] 515. Add async versions of methods
- [ ] 516. Add `async fn generate_text_async(&self, prompt: &str) -> Result<String>`
- [ ] 517. Add `async fn generate_json_async(&self, prompt: &str) -> Result<Value>`
- [ ] 518. Define retry policy trait
- [ ] 519. Add backoff strategy support
- [ ] 520. Add request timeout configuration

### 7.2 Utility Functions (521-535)
- [ ] 521. Create `src/agents/utils.rs` submodule
- [ ] 522. Implement `strip_markdown_fences(text: &str) -> String`
- [ ] 523. Handle ```json fences
- [ ] 524. Handle ``` fences without language
- [ ] 525. Handle nested fences (edge case)
- [ ] 526. Implement `ensure_json_object(text: &str) -> Result<Value>`
- [ ] 527. Strip fences before parsing
- [ ] 528. Parse JSON
- [ ] 529. Validate root is object
- [ ] 530. Return appropriate error for non-objects
- [ ] 531. Implement `is_effectively_empty(text: &str) -> bool`
- [ ] 532. Check for whitespace-only strings
- [ ] 533. Test fence stripping
- [ ] 534. Test JSON parsing
- [ ] 535. Test empty detection

### 7.3 Gemini Agent Implementation (536-565)
- [ ] 536. Create `src/agents/gemini.rs` submodule
- [ ] 537. Define `GeminiAgent` struct
- [ ] 538. Add `config: AgentConfig` field
- [ ] 539. Add `client: reqwest::Client` field
- [ ] 540. Add `api_key: String` field
- [ ] 541. Implement `GeminiAgent::new(config: AgentConfig) -> Result<Self>`
- [ ] 542. Load API key from environment
- [ ] 543. Validate API key presence
- [ ] 544. Create HTTP client with timeout
- [ ] 545. Implement `Agent` trait for GeminiAgent
- [ ] 546. Implement `generate_text` method
- [ ] 547. Build Gemini API request body
- [ ] 548. Set generation config (temperature, top_p, top_k, max_tokens)
- [ ] 549. Make HTTP POST request to Gemini API
- [ ] 550. Parse Gemini API response
- [ ] 551. Extract text from response
- [ ] 552. Handle empty response with retry
- [ ] 553. Handle API errors
- [ ] 554. Implement rate limiting
- [ ] 555. Implement exponential backoff
- [ ] 556. Implement `generate_json` method
- [ ] 557. Call `generate_text` and parse result
- [ ] 558. Add strict JSON prompt suffix if needed
- [ ] 559. Retry with stricter prompt on parse failure
- [ ] 560. Add request logging
- [ ] 561. Add response logging (truncated)
- [ ] 562. Handle safety blocks
- [ ] 563. Test Gemini agent with mocked HTTP
- [ ] 564. Test retry logic
- [ ] 565. Test error handling

### 7.4 OpenAI Agent Implementation (566-585)
- [ ] 566. Create `src/agents/openai.rs` submodule
- [ ] 567. Define `OpenAIAgent` struct
- [ ] 568. Add necessary fields
- [ ] 569. Implement `OpenAIAgent::new(config: AgentConfig) -> Result<Self>`
- [ ] 570. Load API key from OPENAI_API_KEY env
- [ ] 571. Implement `Agent` trait for OpenAIAgent
- [ ] 572. Implement `generate_text` for OpenAI
- [ ] 573. Build chat completion request
- [ ] 574. Set model, temperature, max_tokens
- [ ] 575. Make HTTP POST request
- [ ] 576. Parse OpenAI response format
- [ ] 577. Handle OpenAI-specific errors
- [ ] 578. Implement rate limiting for OpenAI
- [ ] 579. Implement `generate_json` for OpenAI
- [ ] 580. Use JSON mode if available
- [ ] 581. Test OpenAI agent
- [ ] 582. Handle function calling (optional)
- [ ] 583. Support GPT-3.5 and GPT-4 models
- [ ] 584. Add token counting
- [ ] 585. Handle context length limits

### 7.5 Anthropic Agent Implementation (586-600)
- [ ] 586. Create `src/agents/anthropic.rs` submodule
- [ ] 587. Define `AnthropicAgent` struct
- [ ] 588. Implement `AnthropicAgent::new(config: AgentConfig) -> Result<Self>`
- [ ] 589. Load API key from ANTHROPIC_API_KEY env
- [ ] 590. Implement `Agent` trait for AnthropicAgent
- [ ] 591. Build Claude API request
- [ ] 592. Set system prompt and user message
- [ ] 593. Parse Claude response format
- [ ] 594. Handle Anthropic-specific errors
- [ ] 595. Implement rate limiting
- [ ] 596. Implement `generate_json`
- [ ] 597. Support Claude 2 and Claude 3 models
- [ ] 598. Handle streaming responses (optional)
- [ ] 599. Test Anthropic agent
- [ ] 600. Add proper error messages for auth failures

---

## Phase 8: Agent Registry & Factory (Items 601-650)

### 8.1 Agent Factory (601-620)
- [ ] 601. Create `src/agents/factory.rs` submodule
- [ ] 602. Implement `create_agent(config: &AgentConfig) -> Result<Box<dyn Agent>>`
- [ ] 603. Match on provider field
- [ ] 604. Create GeminiAgent for "gemini" provider
- [ ] 605. Create OpenAIAgent for "openai" provider
- [ ] 606. Create AnthropicAgent for "anthropic" provider
- [ ] 607. Return error for unknown provider
- [ ] 608. Add Llama agent support (via Together AI or Groq)
- [ ] 609. Create `src/agents/llama.rs` submodule
- [ ] 610. Implement LlamaAgent struct
- [ ] 611. Support Together AI backend
- [ ] 612. Support Groq backend
- [ ] 613. Implement Agent trait for LlamaAgent
- [ ] 614. Add provider aliases (e.g., "claude" -> "anthropic")
- [ ] 615. Add provider detection from model name
- [ ] 616. Implement lazy agent creation
- [ ] 617. Add agent caching/pooling
- [ ] 618. Test factory with all providers
- [ ] 619. Test unknown provider error
- [ ] 620. Add factory logging

### 8.2 Agent Registry (621-650)
- [ ] 621. Create `src/agents/registry.rs` submodule
- [ ] 622. Define `AgentRegistry` struct
- [ ] 623. Add `agents: HashMap<String, Box<dyn Agent>>` field
- [ ] 624. Implement `AgentRegistry::new() -> Self`
- [ ] 625. Implement `register(&mut self, name: &str, agent: Box<dyn Agent>) -> Result<()>`
- [ ] 626. Validate name is non-empty
- [ ] 627. Handle duplicate registration
- [ ] 628. Implement `get(&self, name: &str) -> Result<&dyn Agent>`
- [ ] 629. Return error for missing agent
- [ ] 630. Implement `list(&self) -> Vec<&str>`
- [ ] 631. Return sorted list of agent names
- [ ] 632. Implement `remove(&mut self, name: &str) -> Option<Box<dyn Agent>>`
- [ ] 633. Implement `from_config_dict(agents_cfg: &HashMap<String, AgentConfig>, defaults: &AgentDefaults) -> Result<Self>`
- [ ] 634. Parse agent configs from TOML structure
- [ ] 635. Apply default values for missing fields
- [ ] 636. Create agents for each config entry
- [ ] 637. Register all created agents
- [ ] 638. Define `AgentDefaults` struct
- [ ] 639. Add default_provider, default_model_name fields
- [ ] 640. Add default_temperature, default_top_p, etc.
- [ ] 641. Implement `AgentDefaults::from_config(config: &Config) -> Self`
- [ ] 642. Test registry creation
- [ ] 643. Test agent registration
- [ ] 644. Test agent retrieval
- [ ] 645. Test missing agent error
- [ ] 646. Test from_config_dict
- [ ] 647. Test with multiple providers
- [ ] 648. Add thread-safe registry (RwLock or Arc<Mutex>)
- [ ] 649. Add registry persistence (save/load)
- [ ] 650. Add registry reload functionality

---

## Phase 9: Job Scraper Module (Items 651-750)

### 9.1 Scraper Base Types (651-670)
- [ ] 651. Create `src/scraper/mod.rs` file
- [ ] 652. Define `JobScraper` trait
- [ ] 653. Add `fn name(&self) -> &str` method
- [ ] 654. Add `fn search_jobs(&self, filters: &SearchFilters, max_results: i32) -> Result<Vec<JobPosting>>` method
- [ ] 655. Add `fn get_job_details(&self, job_url: &str) -> Result<Option<JobPosting>>` method
- [ ] 656. Add async versions of methods
- [ ] 657. Define `ScraperError` enum
- [ ] 658. Add `NetworkError` variant
- [ ] 659. Add `ParseError` variant
- [ ] 660. Add `RateLimitError` variant
- [ ] 661. Add `BlockedError` variant (for anti-bot detection)
- [ ] 662. Add `NotSupportedError` variant
- [ ] 663. Define `ScraperConfig` struct
- [ ] 664. Add timeout, retry count fields
- [ ] 665. Add proxy support fields
- [ ] 666. Add user agent configuration
- [ ] 667. Implement error conversions
- [ ] 668. Define scraper source enum
- [ ] 669. Add LinkedIn, Indeed, Glassdoor, Google, ZipRecruiter variants
- [ ] 670. Implement Display for source enum

### 9.2 JobSpy Integration (671-700)
- [ ] 671. Create `src/scraper/jobspy.rs` submodule
- [ ] 672. Define `JobSpyScraper` struct
- [ ] 673. Determine Rust JobSpy integration strategy
- [ ] 674. Option A: Call Python JobSpy via subprocess
- [ ] 675. Option B: Use Rust HTTP client to scrape directly
- [ ] 676. Option C: Create FFI bindings to Python JobSpy
- [ ] 677. Implement chosen integration approach
- [ ] 678. If subprocess: serialize filters to JSON
- [ ] 679. If subprocess: parse JSON output
- [ ] 680. If HTTP: implement LinkedIn scraper
- [ ] 681. If HTTP: implement Indeed scraper
- [ ] 682. If HTTP: implement Glassdoor scraper
- [ ] 683. If HTTP: implement Google Jobs scraper
- [ ] 684. If HTTP: implement ZipRecruiter scraper
- [ ] 685. Handle anti-bot measures
- [ ] 686. Implement request throttling
- [ ] 687. Add random delays between requests
- [ ] 688. Rotate user agents
- [ ] 689. Support proxy rotation
- [ ] 690. Parse job posting HTML
- [ ] 691. Extract structured data from HTML
- [ ] 692. Handle pagination
- [ ] 693. Handle date parsing (various formats)
- [ ] 694. Handle salary parsing
- [ ] 695. Handle location normalization
- [ ] 696. Handle remote flag detection
- [ ] 697. Implement `JobScraper` trait for JobSpyScraper
- [ ] 698. Test scraper with mocked responses
- [ ] 699. Test error handling
- [ ] 700. Add scraper caching

### 9.3 Scraper Manager (701-730)
- [ ] 701. Create `src/scraper/manager.rs` submodule
- [ ] 702. Define `JobScraperManager` struct
- [ ] 703. Add `results_folder: PathBuf` field
- [ ] 704. Add `saved_searches_path: PathBuf` field
- [ ] 705. Add `scrapers: HashMap<String, Box<dyn JobScraper>>` field
- [ ] 706. Implement `JobScraperManager::new(config: &Config) -> Result<Self>`
- [ ] 707. Initialize available scrapers based on config
- [ ] 708. Create results folder if needed
- [ ] 709. Implement `search_jobs(&self, filters: &SearchFilters, sources: &[String], max_results: i32) -> Result<Vec<JobPosting>>`
- [ ] 710. Search across multiple sources
- [ ] 711. Deduplicate results by URL
- [ ] 712. Sort results by relevance
- [ ] 713. Implement `save_results(&self, results: &[JobPosting], filename: &str) -> Result<PathBuf>`
- [ ] 714. Save to TOML format
- [ ] 715. Include metadata (search time, filters)
- [ ] 716. Implement `load_results(&self, path: &Path) -> Result<Vec<JobPosting>>`
- [ ] 717. Load from TOML or JSON
- [ ] 718. Implement `rank_jobs_in_results(&self, path: &Path, top_n: i32, recompute: bool) -> Result<Vec<RankedJob>>`
- [ ] 719. Define `RankedJob` struct with job and score
- [ ] 720. Load results file
- [ ] 721. Score each job if needed
- [ ] 722. Sort by score descending
- [ ] 723. Return top N
- [ ] 724. Implement `export_to_job_descriptions(&self, jobs: &[JobPosting], folder: &Path) -> Result<i32>`
- [ ] 725. Create job description text files
- [ ] 726. Name files based on title/company
- [ ] 727. Handle filename collisions
- [ ] 728. Test manager with multiple sources
- [ ] 729. Test result saving/loading
- [ ] 730. Test job ranking

### 9.4 Saved Search Manager (731-750)
- [ ] 731. Create `src/scraper/saved_search.rs` submodule
- [ ] 732. Define `SavedSearchManager` struct
- [ ] 733. Add `file_path: PathBuf` field
- [ ] 734. Add `searches: HashMap<String, SavedSearch>` field
- [ ] 735. Implement `SavedSearchManager::new(path: &Path) -> Result<Self>`
- [ ] 736. Load saved searches from TOML
- [ ] 737. Implement `save(&self, search: SavedSearch) -> Result<()>`
- [ ] 738. Add or update search by name
- [ ] 739. Persist to file
- [ ] 740. Implement `get(&self, name: &str) -> Option<&SavedSearch>`
- [ ] 741. Implement `list(&self) -> Vec<&str>`
- [ ] 742. Implement `delete(&mut self, name: &str) -> Result<()>`
- [ ] 743. Implement `update_last_run(&mut self, name: &str) -> Result<()>`
- [ ] 744. Implement `run_search(&self, name: &str, manager: &JobScraperManager) -> Result<Vec<JobPosting>>`
- [ ] 745. Load saved search by name
- [ ] 746. Execute search with saved filters
- [ ] 747. Update last_run timestamp
- [ ] 748. Test saved search persistence
- [ ] 749. Test search execution
- [ ] 750. Test CRUD operations

---

## Phase 10: Input Handler Module (Items 751-800)

### 10.1 Input Handler Structure (751-770)
- [ ] 751. Create `src/input/mod.rs` file
- [ ] 752. Define `InputHandler` struct
- [ ] 753. Add `resumes_folder: PathBuf` field
- [ ] 754. Add `job_descriptions_folder: PathBuf` field
- [ ] 755. Add `tesseract_cmd: Option<String>` field
- [ ] 756. Implement `InputHandler::new(config: &Config) -> Self`
- [ ] 757. Implement `list_resumes(&self) -> Result<Vec<PathBuf>>`
- [ ] 758. Find all files in resumes folder
- [ ] 759. Filter by supported extensions
- [ ] 760. Sort by modification time
- [ ] 761. Implement `list_job_descriptions(&self) -> Result<Vec<PathBuf>>`
- [ ] 762. Find all files in job descriptions folder
- [ ] 763. Filter by supported extensions
- [ ] 764. Implement `load_resume(&self, path: &Path) -> Result<String>`
- [ ] 765. Detect file type
- [ ] 766. Extract text using appropriate method
- [ ] 767. Call OCR for images if configured
- [ ] 768. Implement `load_job_description(&self, path: &Path) -> Result<String>`
- [ ] 769. Extract text from job description file
- [ ] 770. Handle various formats

### 10.2 File Selection (771-790)
- [ ] 771. Implement `select_resume_interactive(&self) -> Result<Option<PathBuf>>`
- [ ] 772. List available resumes
- [ ] 773. Display numbered menu
- [ ] 774. Read user selection
- [ ] 775. Implement `select_job_description_interactive(&self) -> Result<Option<PathBuf>>`
- [ ] 776. List available job descriptions
- [ ] 777. Handle empty folder
- [ ] 778. Implement `select_multiple_resumes(&self) -> Result<Vec<PathBuf>>`
- [ ] 779. Allow multi-select
- [ ] 780. Implement "all" option
- [ ] 781. Implement `get_new_resumes(&self, state: &StateManager) -> Result<Vec<PathBuf>>`
- [ ] 782. List all resumes
- [ ] 783. Filter out already processed
- [ ] 784. Use file hash for comparison
- [ ] 785. Implement resume validation
- [ ] 786. Check file is not empty
- [ ] 787. Check file is readable
- [ ] 788. Warn for very small files
- [ ] 789. Test input handler
- [ ] 790. Test with various file types

### 10.3 OCR Support (791-800)
- [ ] 791. Create `src/input/ocr.rs` submodule
- [ ] 792. Implement `run_tesseract(image_path: &Path, tesseract_cmd: &str) -> Result<String>`
- [ ] 793. Build Tesseract command
- [ ] 794. Execute subprocess
- [ ] 795. Capture stdout
- [ ] 796. Handle Tesseract errors
- [ ] 797. Implement language detection (optional)
- [ ] 798. Support multiple languages
- [ ] 799. Test OCR functionality
- [ ] 800. Handle missing Tesseract gracefully

---

## Phase 11: Output Generator Module (Items 801-880)

### 11.1 Output Types (801-820)
- [ ] 801. Create `src/output/mod.rs` file
- [ ] 802. Define `OutputFormat` enum
- [ ] 803. Add `Json`, `Toml`, `Txt`, `Markdown`, `All` variants
- [ ] 804. Implement `FromStr` for OutputFormat
- [ ] 805. Implement `Display` for OutputFormat
- [ ] 806. Define `OutputConfig` struct
- [ ] 807. Add `format: OutputFormat` field
- [ ] 808. Add `output_folder: PathBuf` field
- [ ] 809. Add `subdir_pattern: String` field
- [ ] 810. Add `include_metadata: bool` field
- [ ] 811. Define `OutputResult` struct
- [ ] 812. Add generated file paths
- [ ] 813. Add generation timestamp
- [ ] 814. Add any warnings
- [ ] 815. Define `ResumeOutput` struct
- [ ] 816. Add structured data field
- [ ] 817. Add scores field
- [ ] 818. Add recommendations field
- [ ] 819. Add metadata field
- [ ] 820. Derive traits for all output types

### 11.2 Output Path Generation (821-840)
- [ ] 821. Create `src/output/path.rs` submodule
- [ ] 822. Implement `generate_output_path(pattern: &str, vars: &HashMap<String, String>) -> PathBuf`
- [ ] 823. Support `{resume_name}` placeholder
- [ ] 824. Support `{job_title}` placeholder
- [ ] 825. Support `{timestamp}` placeholder
- [ ] 826. Support `{date}` placeholder
- [ ] 827. Support `{version}` placeholder
- [ ] 828. Sanitize path components
- [ ] 829. Handle missing variables
- [ ] 830. Implement `generate_filename(base: &str, format: OutputFormat) -> String`
- [ ] 831. Add appropriate extension
- [ ] 832. Implement `ensure_unique_path(path: &Path) -> PathBuf`
- [ ] 833. Add numeric suffix if exists
- [ ] 834. Implement path validation
- [ ] 835. Check path length limits
- [ ] 836. Check for invalid characters
- [ ] 837. Test path generation
- [ ] 838. Test with various patterns
- [ ] 839. Test uniqueness logic
- [ ] 840. Test sanitization

### 11.3 Format Writers (841-865)
- [ ] 841. Create `src/output/writers.rs` submodule
- [ ] 842. Implement `write_json(path: &Path, data: &Value) -> Result<()>`
- [ ] 843. Pretty-print with indentation
- [ ] 844. Handle special characters
- [ ] 845. Implement `write_toml(path: &Path, data: &Value) -> Result<()>`
- [ ] 846. Convert JSON value to TOML
- [ ] 847. Handle TOML-specific formatting
- [ ] 848. Implement `write_txt(path: &Path, content: &str) -> Result<()>`
- [ ] 849. Handle line endings (platform-specific or normalize)
- [ ] 850. Implement `write_markdown(path: &Path, content: &str) -> Result<()>`
- [ ] 851. Implement `format_resume_as_txt(resume: &Value) -> String`
- [ ] 852. Format contact info section
- [ ] 853. Format summary section
- [ ] 854. Format experience section
- [ ] 855. Format education section
- [ ] 856. Format skills section
- [ ] 857. Format certifications section
- [ ] 858. Format projects section
- [ ] 859. Add section headers and separators
- [ ] 860. Implement `format_resume_as_markdown(resume: &Value) -> String`
- [ ] 861. Use markdown headers
- [ ] 862. Use bullet points
- [ ] 863. Test all writers
- [ ] 864. Test with edge cases
- [ ] 865. Test Unicode handling

### 11.4 Output Generator (866-880)
- [ ] 866. Create `src/output/generator.rs` submodule
- [ ] 867. Define `OutputGenerator` struct
- [ ] 868. Add `config: OutputConfig` field
- [ ] 869. Implement `OutputGenerator::new(config: OutputConfig) -> Self`
- [ ] 870. Implement `generate(&self, output: &ResumeOutput) -> Result<OutputResult>`
- [ ] 871. Create output directory structure
- [ ] 872. Write files in all configured formats
- [ ] 873. Generate manifest file
- [ ] 874. Generate scores file
- [ ] 875. Implement `generate_manifest(&self, output: &ResumeOutput, paths: &[PathBuf]) -> Result<PathBuf>`
- [ ] 876. Include processing metadata
- [ ] 877. Implement `generate_scores_file(&self, scores: &ScoreReport) -> Result<PathBuf>`
- [ ] 878. Test output generator
- [ ] 879. Test with all formats
- [ ] 880. Test manifest generation

---

## Phase 12: Resume Processor Module (Items 881-960)

### 12.1 Processor Structure (881-900)
- [ ] 881. Create `src/processor/mod.rs` file
- [ ] 882. Define `ResumeProcessor` struct
- [ ] 883. Add `config: Config` field
- [ ] 884. Add `state_manager: StateManager` field
- [ ] 885. Add `agent_registry: AgentRegistry` field
- [ ] 886. Add `input_handler: InputHandler` field
- [ ] 887. Add `output_generator: OutputGenerator` field
- [ ] 888. Implement `ResumeProcessor::new(config: Config) -> Result<Self>`
- [ ] 889. Initialize all components
- [ ] 890. Validate configuration
- [ ] 891. Load state
- [ ] 892. Create agent registry
- [ ] 893. Define `ProcessingResult` struct
- [ ] 894. Add `resume_path: PathBuf` field
- [ ] 895. Add `output_paths: Vec<PathBuf>` field
- [ ] 896. Add `scores: Option<ScoreReport>` field
- [ ] 897. Add `iterations: i32` field
- [ ] 898. Add `success: bool` field
- [ ] 899. Add `error: Option<String>` field
- [ ] 900. Derive traits for ProcessingResult

### 12.2 Core Processing Logic (901-930)
- [ ] 901. Implement `process_resume(&mut self, resume_path: &Path, job_path: Option<&Path>) -> Result<ProcessingResult>`
- [ ] 902. Check if already processed
- [ ] 903. Load resume content
- [ ] 904. Load job description if provided
- [ ] 905. Call AI enhancement
- [ ] 906. Validate enhanced output schema
- [ ] 907. Retry enhancement on schema failure
- [ ] 908. Score enhanced resume
- [ ] 909. Run iteration loop if enabled
- [ ] 910. Generate outputs
- [ ] 911. Update state
- [ ] 912. Return result
- [ ] 913. Implement `enhance_resume(&self, content: &str, job_desc: Option<&str>) -> Result<Value>`
- [ ] 914. Build enhancement prompt
- [ ] 915. Include job description context
- [ ] 916. Call enhancer agent
- [ ] 917. Parse JSON response
- [ ] 918. Validate structure
- [ ] 919. Implement `revise_resume(&self, resume: &Value, feedback: &str) -> Result<Value>`
- [ ] 920. Build revision prompt with current resume and feedback
- [ ] 921. Call reviser agent
- [ ] 922. Parse and validate response
- [ ] 923. Implement `summarize_job(&self, job_desc: &str) -> Result<Value>`
- [ ] 924. Build summarization prompt
- [ ] 925. Call summarizer agent
- [ ] 926. Parse response
- [ ] 927. Implement `process_all_resumes(&mut self, job_path: Option<&Path>) -> Result<Vec<ProcessingResult>>`
- [ ] 928. Get list of unprocessed resumes
- [ ] 929. Process each resume
- [ ] 930. Handle partial failures

### 12.3 Iteration Logic (931-950)
- [ ] 931. Create `src/processor/iteration.rs` submodule
- [ ] 932. Define `IterationStrategy` enum
- [ ] 933. Add `BestOf`, `FirstHit`, `Patience` variants
- [ ] 934. Implement `FromStr` for IterationStrategy
- [ ] 935. Define `IterationState` struct
- [ ] 936. Add `current_best: Option<Value>` field
- [ ] 937. Add `best_score: f64` field
- [ ] 938. Add `iteration_count: i32` field
- [ ] 939. Add `consecutive_regressions: i32` field
- [ ] 940. Implement `run_iteration_loop(&mut self, initial: Value, target: f64, max_iter: i32, strategy: IterationStrategy) -> Result<(Value, ScoreReport)>`
- [ ] 941. Initialize iteration state
- [ ] 942. Loop until target or max iterations
- [ ] 943. Generate feedback from scores
- [ ] 944. Revise resume
- [ ] 945. Score new version
- [ ] 946. Apply strategy logic
- [ ] 947. Track regressions
- [ ] 948. Implement early stopping conditions
- [ ] 949. Return best version
- [ ] 950. Test iteration strategies

### 12.4 PDF Extraction (951-960)
- [ ] 951. Create `src/processor/pdf.rs` submodule
- [ ] 952. Implement `extract_pdf_text(path: &Path) -> Result<String>`
- [ ] 953. Use pdf-extract or lopdf crate
- [ ] 954. Handle multi-page PDFs
- [ ] 955. Handle text extraction failures
- [ ] 956. Detect scanned PDFs
- [ ] 957. Return appropriate error for encrypted PDFs
- [ ] 958. Normalize extracted whitespace
- [ ] 959. Test PDF extraction
- [ ] 960. Test with various PDF types

---

## Phase 13: Recommendations Module (Items 961-1000)

### 13.1 Recommendation Types (961-975)
- [ ] 961. Create `src/recommendations/mod.rs` file
- [ ] 962. Define `Recommendation` struct
- [ ] 963. Add `message: String` field
- [ ] 964. Add `reason: Option<String>` field
- [ ] 965. Add `severity: Severity` field
- [ ] 966. Add `meta: Option<HashMap<String, Value>>` field
- [ ] 967. Define `Severity` enum
- [ ] 968. Add `Info`, `Warning`, `Critical` variants
- [ ] 969. Implement `Display` for Severity
- [ ] 970. Derive traits for Recommendation
- [ ] 971. Implement `Recommendation::new(message: &str) -> Self`
- [ ] 972. Implement builder pattern for Recommendation
- [ ] 973. Add `with_reason()` method
- [ ] 974. Add `with_severity()` method
- [ ] 975. Add `with_meta()` method

### 13.2 Recommendation Generation (976-1000)
- [ ] 976. Create `src/recommendations/generator.rs` submodule
- [ ] 977. Implement `generate_recommendations(scoring: &Value, max_items: i32) -> Vec<Recommendation>`
- [ ] 978. Extract scoring reports from payload
- [ ] 979. Analyze resume scores
- [ ] 980. Generate recommendations for low resume scores
- [ ] 981. Check experience section completeness
- [ ] 982. Check skills section
- [ ] 983. Check education section
- [ ] 984. Check summary quality
- [ ] 985. Analyze match scores
- [ ] 986. Generate recommendations for low match scores
- [ ] 987. Recommend adding missing keywords
- [ ] 988. Recommend skill additions
- [ ] 989. Recommend experience alignment
- [ ] 990. Analyze job scores
- [ ] 991. Warn about low quality job postings
- [ ] 992. Prioritize recommendations by severity
- [ ] 993. Limit to max_items
- [ ] 994. Deduplicate similar recommendations
- [ ] 995. Format recommendations for display
- [ ] 996. Implement `format_recommendations(recs: &[Recommendation]) -> String`
- [ ] 997. Test recommendation generation
- [ ] 998. Test with various scoring scenarios
- [ ] 999. Test priority ordering
- [ ] 1000. Test max items limiting

---

## Phase 14: Schema Validation Module (Items 1001-1050)

### 14.1 Validation Types (1001-1015)
- [ ] 1001. Create `src/validation/mod.rs` file
- [ ] 1002. Define `ValidationResult` struct
- [ ] 1003. Add `ok: bool` field
- [ ] 1004. Add `errors: Vec<String>` field
- [ ] 1005. Add `summary: String` field
- [ ] 1006. Add `detail: Option<String>` field
- [ ] 1007. Derive traits for ValidationResult
- [ ] 1008. Implement `ValidationResult::success() -> Self`
- [ ] 1009. Implement `ValidationResult::failure(errors: Vec<String>) -> Self`
- [ ] 1010. Implement `ValidationResult::as_dict() -> HashMap<...>`
- [ ] 1011. Add `is_ok()` convenience method
- [ ] 1012. Add `first_error()` method
- [ ] 1013. Add `all_errors()` method
- [ ] 1014. Implement `Display` for ValidationResult
- [ ] 1015. Implement `Debug` for ValidationResult

### 14.2 JSON Schema Validation (1016-1035)
- [ ] 1016. Add `jsonschema` crate dependency
- [ ] 1017. Implement `schema_validation_available() -> bool`
- [ ] 1018. Check if jsonschema feature is enabled
- [ ] 1019. Implement `load_schema(path: &Path) -> Result<Value>`
- [ ] 1020. Read schema file
- [ ] 1021. Parse JSON
- [ ] 1022. Validate schema structure
- [ ] 1023. Implement `validate_json(instance: &Value, schema: &Value, name: &str) -> ValidationResult`
- [ ] 1024. Use jsonschema crate for validation
- [ ] 1025. Collect all validation errors
- [ ] 1026. Format errors for readability
- [ ] 1027. Implement `validate_json_str(json_str: &str, schema: &Value) -> ValidationResult`
- [ ] 1028. Parse JSON string first
- [ ] 1029. Then validate
- [ ] 1030. Implement `format_validation_errors(errors: &[ValidationError]) -> String`
- [ ] 1031. Include path to error
- [ ] 1032. Include expected vs actual
- [ ] 1033. Include validator keyword
- [ ] 1034. Test schema validation
- [ ] 1035. Test with resume schema

### 14.3 Error Formatting (1036-1050)
- [ ] 1036. Implement `_format_error_path(error: &ValidationError) -> String`
- [ ] 1037. Convert JSON pointer to readable path
- [ ] 1038. Handle array indices
- [ ] 1039. Handle nested objects
- [ ] 1040. Implement `_format_schema_path(error: &ValidationError) -> String`
- [ ] 1041. Show which part of schema failed
- [ ] 1042. Implement `_compact(value: &Value, max_len: usize) -> String`
- [ ] 1043. Truncate long values
- [ ] 1044. Handle UTF-8 boundaries
- [ ] 1045. Implement `_first_lines(text: &str, max_lines: usize) -> Vec<String>`
- [ ] 1046. Extract first N non-empty lines
- [ ] 1047. Test error formatting
- [ ] 1048. Test with nested errors
- [ ] 1049. Test with array errors
- [ ] 1050. Test truncation

---

## Phase 15: CLI Module (Items 1051-1150)

### 15.1 Main CLI Structure (1051-1075)
- [ ] 1051. Create `src/bin/main.rs` file
- [ ] 1052. Add clap dependency with derive feature
- [ ] 1053. Define `Cli` struct with clap derive
- [ ] 1054. Add `config_file` argument with default
- [ ] 1055. Add subcommands enum
- [ ] 1056. Add `Interactive` subcommand (default)
- [ ] 1057. Add `Process` subcommand
- [ ] 1058. Add `ScoreResume` subcommand
- [ ] 1059. Add `ScoreMatch` subcommand
- [ ] 1060. Add `RankJobs` subcommand
- [ ] 1061. Add `Search` subcommand (job search)
- [ ] 1062. Add global verbosity flag
- [ ] 1063. Add quiet flag
- [ ] 1064. Implement `main()` function
- [ ] 1065. Parse CLI arguments
- [ ] 1066. Initialize logging
- [ ] 1067. Load configuration
- [ ] 1068. Dispatch to subcommand handler
- [ ] 1069. Handle errors with appropriate exit codes
- [ ] 1070. Add colored error output
- [ ] 1071. Add version flag
- [ ] 1072. Add help text for all commands
- [ ] 1073. Add examples in help
- [ ] 1074. Test CLI parsing
- [ ] 1075. Test help output

### 15.2 Interactive Menu (1076-1100)
- [ ] 1076. Create `src/cli/menu.rs` submodule
- [ ] 1077. Implement `run_interactive_menu(config: &Config) -> Result<()>`
- [ ] 1078. Display main menu
- [ ] 1079. Option 1: Process resumes
- [ ] 1080. Option 2: Convert files
- [ ] 1081. Option 3: Job search
- [ ] 1082. Option 4: View/edit settings
- [ ] 1083. Option 5: View available files
- [ ] 1084. Option 6: View outputs
- [ ] 1085. Option 7: Test OCR
- [ ] 1086. Option 0: Exit
- [ ] 1087. Read user input
- [ ] 1088. Dispatch to submenu
- [ ] 1089. Handle invalid input
- [ ] 1090. Loop until exit
- [ ] 1091. Implement `process_resumes_menu(processor: &mut ResumeProcessor) -> Result<()>`
- [ ] 1092. Option to process all
- [ ] 1093. Option to process with job description
- [ ] 1094. Option to process specific resume
- [ ] 1095. Implement `job_search_menu(manager: &JobScraperManager) -> Result<()>`
- [ ] 1096. New search
- [ ] 1097. Load saved search
- [ ] 1098. View results
- [ ] 1099. Test interactive menu flow
- [ ] 1100. Handle Ctrl+C gracefully

### 15.3 Score Resume Subcommand (1101-1115)
- [ ] 1101. Define `ScoreResumeArgs` struct
- [ ] 1102. Add `resume` path argument (required)
- [ ] 1103. Add `weights` path argument (optional)
- [ ] 1104. Add `write_back` flag
- [ ] 1105. Add `json` output flag
- [ ] 1106. Implement `cmd_score_resume(args: ScoreResumeArgs, config: &Config) -> Result<i32>`
- [ ] 1107. Load structured resume (JSON or TOML)
- [ ] 1108. Load scoring weights
- [ ] 1109. Call `score_resume()` function
- [ ] 1110. Build scoring payload
- [ ] 1111. If write_back, update resume file
- [ ] 1112. Print results (JSON or formatted)
- [ ] 1113. Test score-resume command
- [ ] 1114. Test with JSON resume
- [ ] 1115. Test with TOML resume

### 15.4 Score Match Subcommand (1116-1130)
- [ ] 1116. Define `ScoreMatchArgs` struct
- [ ] 1117. Add `resume` path argument
- [ ] 1118. Add `job` path argument
- [ ] 1119. Add `weights` path argument (optional)
- [ ] 1120. Add `write_back` flag
- [ ] 1121. Add `json` output flag
- [ ] 1122. Implement `cmd_score_match(args: ScoreMatchArgs, config: &Config) -> Result<i32>`
- [ ] 1123. Load structured resume
- [ ] 1124. Load job description text
- [ ] 1125. Build job object for scoring
- [ ] 1126. Call `score_resume()` and `score_match()`
- [ ] 1127. Compute iteration score
- [ ] 1128. Build combined scoring payload
- [ ] 1129. Output results
- [ ] 1130. Test score-match command

### 15.5 Rank Jobs Subcommand (1131-1150)
- [ ] 1131. Define `RankJobsArgs` struct
- [ ] 1132. Add `results` path argument
- [ ] 1133. Add `top` count argument (default 20)
- [ ] 1134. Add `no_recompute` flag
- [ ] 1135. Add `export_top` count argument
- [ ] 1136. Add `json` output flag
- [ ] 1137. Implement `cmd_rank_jobs(args: RankJobsArgs, config: &Config) -> Result<i32>`
- [ ] 1138. Initialize scraper manager
- [ ] 1139. Resolve results file path
- [ ] 1140. Call `rank_jobs_in_results()`
- [ ] 1141. Print ranked results
- [ ] 1142. If export_top, export job descriptions
- [ ] 1143. Format output (JSON or table)
- [ ] 1144. Implement table formatting for terminal
- [ ] 1145. Show rank, title, score, company, location, URL
- [ ] 1146. Test rank-jobs command
- [ ] 1147. Test with various result files
- [ ] 1148. Test export functionality
- [ ] 1149. Handle empty results
- [ ] 1150. Handle missing file error

---

## Phase 16: TOML I/O Module (Items 1151-1200)

### 16.1 TOML Parser (1151-1170)
- [ ] 1151. Create `src/toml_io/mod.rs` file
- [ ] 1152. Decide: use existing `toml` crate or custom parser
- [ ] 1153. If using toml crate, create wrapper functions
- [ ] 1154. Implement `loads(toml_str: &str) -> Result<Value>`
- [ ] 1155. Parse TOML string to serde_json Value
- [ ] 1156. Handle parse errors with line numbers
- [ ] 1157. Implement `load(path: &Path) -> Result<Value>`
- [ ] 1158. Read file content
- [ ] 1159. Call `loads()`
- [ ] 1160. Add file path to error context
- [ ] 1161. Handle file not found
- [ ] 1162. Handle encoding issues
- [ ] 1163. Implement `load_as<T: DeserializeOwned>(path: &Path) -> Result<T>`
- [ ] 1164. Deserialize directly to type
- [ ] 1165. Test TOML loading
- [ ] 1166. Test with nested tables
- [ ] 1167. Test with arrays
- [ ] 1168. Test with inline tables
- [ ] 1169. Test error messages
- [ ] 1170. Benchmark parsing performance

### 16.2 TOML Writer (1171-1190)
- [ ] 1171. Implement `dumps(value: &Value) -> Result<String>`
- [ ] 1172. Convert serde_json Value to TOML string
- [ ] 1173. Handle nested tables properly
- [ ] 1174. Handle arrays of tables
- [ ] 1175. Handle inline arrays
- [ ] 1176. Implement proper TOML string escaping
- [ ] 1177. Handle special characters
- [ ] 1178. Handle multiline strings
- [ ] 1179. Implement `dump(value: &Value, path: &Path) -> Result<()>`
- [ ] 1180. Call `dumps()` to get string
- [ ] 1181. Use atomic write
- [ ] 1182. Implement `dump_as<T: Serialize>(value: &T, path: &Path) -> Result<()>`
- [ ] 1183. Serialize type to TOML
- [ ] 1184. Test TOML writing
- [ ] 1185. Test round-trip (load -> dump -> load)
- [ ] 1186. Test with complex nested structures
- [ ] 1187. Test with state manager format
- [ ] 1188. Test with config format
- [ ] 1189. Test string escaping
- [ ] 1190. Test Unicode handling

### 16.3 TOML Value Helpers (1191-1200)
- [ ] 1191. Implement `format_toml_value(value: &Value) -> String`
- [ ] 1192. Format single values (not full documents)
- [ ] 1193. Implement `toml_to_json(toml: &toml::Value) -> serde_json::Value`
- [ ] 1194. Convert between value types
- [ ] 1195. Implement `json_to_toml(json: &serde_json::Value) -> toml::Value`
- [ ] 1196. Handle incompatible types (null)
- [ ] 1197. Implement `merge_toml(base: Value, overlay: Value) -> Value`
- [ ] 1198. Deep merge for config overlays
- [ ] 1199. Test value conversions
- [ ] 1200. Test merge functionality

---

## Phase 17: Gemini Integrator Module (Items 1201-1280)

### 17.1 Gemini Client (1201-1220)
- [ ] 1201. Create `src/gemini/mod.rs` file
- [ ] 1202. Define `GeminiClient` struct
- [ ] 1203. Add `api_key: String` field
- [ ] 1204. Add `http_client: reqwest::Client` field
- [ ] 1205. Add `base_url: String` field (configurable)
- [ ] 1206. Implement `GeminiClient::new(api_key: &str) -> Result<Self>`
- [ ] 1207. Validate API key format
- [ ] 1208. Create HTTP client with timeout
- [ ] 1209. Define Gemini API request types
- [ ] 1210. Define `GenerateContentRequest` struct
- [ ] 1211. Add `contents: Vec<Content>` field
- [ ] 1212. Add `generation_config: GenerationConfig` field
- [ ] 1213. Define `Content` struct with parts
- [ ] 1214. Define `GenerationConfig` struct
- [ ] 1215. Add temperature, top_p, top_k, max_output_tokens
- [ ] 1216. Define Gemini API response types
- [ ] 1217. Define `GenerateContentResponse` struct
- [ ] 1218. Define `Candidate` struct
- [ ] 1219. Define `ContentPart` struct
- [ ] 1220. Derive Serialize/Deserialize for all types

### 17.2 API Methods (1221-1245)
- [ ] 1221. Implement `generate_content(&self, request: GenerateContentRequest) -> Result<GenerateContentResponse>`
- [ ] 1222. Build API URL with model name
- [ ] 1223. Serialize request to JSON
- [ ] 1224. Make POST request
- [ ] 1225. Handle HTTP errors
- [ ] 1226. Parse response JSON
- [ ] 1227. Handle API errors in response
- [ ] 1228. Implement retry logic with backoff
- [ ] 1229. Implement `generate_text(&self, prompt: &str, config: &GenerationConfig) -> Result<String>`
- [ ] 1230. Build request from prompt
- [ ] 1231. Call generate_content
- [ ] 1232. Extract text from response
- [ ] 1233. Handle blocked responses
- [ ] 1234. Implement `generate_json(&self, prompt: &str, config: &GenerationConfig) -> Result<Value>`
- [ ] 1235. Call generate_text
- [ ] 1236. Strip markdown fences
- [ ] 1237. Parse JSON
- [ ] 1238. Retry with stricter prompt on failure
- [ ] 1239. Implement rate limiting
- [ ] 1240. Add request throttling
- [ ] 1241. Track requests per minute
- [ ] 1242. Wait if limit exceeded
- [ ] 1243. Add request logging
- [ ] 1244. Log request (prompt truncated)
- [ ] 1245. Log response (truncated)

### 17.3 Multi-Agent Support (1246-1270)
- [ ] 1246. Create `src/gemini/integrator.rs` submodule
- [ ] 1247. Define `GeminiIntegrator` struct
- [ ] 1248. Add `client: GeminiClient` field
- [ ] 1249. Add `agents: HashMap<String, AgentConfig>` field
- [ ] 1250. Implement `GeminiIntegrator::new(config: &Config) -> Result<Self>`
- [ ] 1251. Load agent configs from config
- [ ] 1252. Create client with API key
- [ ] 1253. Implement `enhance_resume(&self, content: &str, job_summary: Option<&str>) -> Result<Value>`
- [ ] 1254. Get enhancer agent config
- [ ] 1255. Build enhancement prompt
- [ ] 1256. Include resume content
- [ ] 1257. Include job context if provided
- [ ] 1258. Call generate_json
- [ ] 1259. Validate response structure
- [ ] 1260. Implement `revise_resume(&self, resume: &Value, feedback: &str) -> Result<Value>`
- [ ] 1261. Get reviser agent config
- [ ] 1262. Build revision prompt
- [ ] 1263. Call generate_json
- [ ] 1264. Implement `summarize_job(&self, job_desc: &str) -> Result<Value>`
- [ ] 1265. Get summarizer agent config
- [ ] 1266. Build summarization prompt
- [ ] 1267. Call generate_json
- [ ] 1268. Test multi-agent calls
- [ ] 1269. Test with mocked HTTP
- [ ] 1270. Test error handling

### 17.4 Prompt Templates (1271-1280)
- [ ] 1271. Create `src/gemini/prompts.rs` submodule
- [ ] 1272. Define enhancement prompt template
- [ ] 1273. Define revision prompt template
- [ ] 1274. Define summarization prompt template
- [ ] 1275. Define scoring prompt template (if AI-based)
- [ ] 1276. Implement template variable substitution
- [ ] 1277. Handle escaping in templates
- [ ] 1278. Add prompt validation
- [ ] 1279. Test prompt generation
- [ ] 1280. Test with various inputs

---

## Phase 18: Integration & Testing (Items 1281-1380)

### 18.1 Integration Tests (1281-1310)
- [ ] 1281. Create `tests/` directory structure
- [ ] 1282. Create `tests/common/mod.rs` for test utilities
- [ ] 1283. Create test fixtures directory
- [ ] 1284. Add sample resume files (TXT, JSON, TOML)
- [ ] 1285. Add sample job description files
- [ ] 1286. Add sample config files
- [ ] 1287. Write integration test: config loading
- [ ] 1288. Write integration test: state management
- [ ] 1289. Write integration test: file hashing
- [ ] 1290. Write integration test: text extraction
- [ ] 1291. Write integration test: PDF extraction
- [ ] 1292. Write integration test: scoring
- [ ] 1293. Write integration test: recommendations
- [ ] 1294. Write integration test: output generation
- [ ] 1295. Write integration test: TOML I/O
- [ ] 1296. Write integration test: schema validation
- [ ] 1297. Write integration test: CLI parsing
- [ ] 1298. Write integration test: interactive menu (mocked input)
- [ ] 1299. Write integration test: full processing pipeline
- [ ] 1300. Write integration test: job scraping (mocked)
- [ ] 1301. Write integration test: agent registry
- [ ] 1302. Write integration test: iteration loop
- [ ] 1303. Test error propagation
- [ ] 1304. Test graceful degradation
- [ ] 1305. Test concurrent operations
- [ ] 1306. Test file locking
- [ ] 1307. Test cross-platform paths
- [ ] 1308. Test Unicode handling throughout
- [ ] 1309. Test large file handling
- [ ] 1310. Test memory usage

### 18.2 Unit Tests by Module (1311-1340)
- [ ] 1311. Ensure 80%+ code coverage for config module
- [ ] 1312. Ensure 80%+ code coverage for state module
- [ ] 1313. Ensure 80%+ code coverage for utils module
- [ ] 1314. Ensure 80%+ code coverage for scoring module
- [ ] 1315. Ensure 80%+ code coverage for agents module
- [ ] 1316. Ensure 80%+ code coverage for scraper module
- [ ] 1317. Ensure 80%+ code coverage for input module
- [ ] 1318. Ensure 80%+ code coverage for output module
- [ ] 1319. Ensure 80%+ code coverage for processor module
- [ ] 1320. Ensure 80%+ code coverage for recommendations module
- [ ] 1321. Ensure 80%+ code coverage for validation module
- [ ] 1322. Ensure 80%+ code coverage for cli module
- [ ] 1323. Ensure 80%+ code coverage for toml_io module
- [ ] 1324. Ensure 80%+ code coverage for gemini module
- [ ] 1325. Add property-based tests for parsing
- [ ] 1326. Add property-based tests for serialization
- [ ] 1327. Add property-based tests for path handling
- [ ] 1328. Add fuzz tests for TOML parsing
- [ ] 1329. Add fuzz tests for JSON parsing
- [ ] 1330. Add fuzz tests for text extraction
- [ ] 1331. Add regression tests for fixed bugs
- [ ] 1332. Add tests for edge cases
- [ ] 1333. Add tests for error conditions
- [ ] 1334. Add tests for boundary values
- [ ] 1335. Add tests for empty inputs
- [ ] 1336. Add tests for null/None handling
- [ ] 1337. Add tests for very large inputs
- [ ] 1338. Add tests for special characters
- [ ] 1339. Add tests for concurrent access
- [ ] 1340. Document all test cases

### 18.3 Benchmarks (1341-1360)
- [ ] 1341. Create `benches/` directory
- [ ] 1342. Add criterion benchmark for file hashing
- [ ] 1343. Add criterion benchmark for text extraction
- [ ] 1344. Add criterion benchmark for PDF extraction
- [ ] 1345. Add criterion benchmark for scoring
- [ ] 1346. Add criterion benchmark for TOML parsing
- [ ] 1347. Add criterion benchmark for TOML writing
- [ ] 1348. Add criterion benchmark for JSON parsing
- [ ] 1349. Add criterion benchmark for config loading
- [ ] 1350. Add criterion benchmark for state operations
- [ ] 1351. Add criterion benchmark for path generation
- [ ] 1352. Add criterion benchmark for validation
- [ ] 1353. Add criterion benchmark for keyword extraction
- [ ] 1354. Compare benchmarks against Python version
- [ ] 1355. Document performance improvements
- [ ] 1356. Identify performance bottlenecks
- [ ] 1357. Optimize critical paths
- [ ] 1358. Add memory usage benchmarks
- [ ] 1359. Add startup time benchmarks
- [ ] 1360. Add end-to-end processing benchmarks

### 18.4 CI/CD Setup (1361-1380)
- [ ] 1361. Create `.github/workflows/` directory
- [ ] 1362. Create `ci.yml` workflow file
- [ ] 1363. Add build job for Linux
- [ ] 1364. Add build job for macOS
- [ ] 1365. Add build job for Windows
- [ ] 1366. Add test job with coverage
- [ ] 1367. Add clippy lint job
- [ ] 1368. Add rustfmt check job
- [ ] 1369. Add security audit job (cargo-audit)
- [ ] 1370. Add documentation build job
- [ ] 1371. Add release build job
- [ ] 1372. Configure caching for dependencies
- [ ] 1373. Configure artifact upload
- [ ] 1374. Add coverage reporting (codecov/coveralls)
- [ ] 1375. Add badge to README
- [ ] 1376. Create release workflow
- [ ] 1377. Auto-publish to crates.io (optional)
- [ ] 1378. Build and publish binaries
- [ ] 1379. Add changelog generation
- [ ] 1380. Set up dependabot for dependency updates

---

## Phase 19: Documentation (Items 1381-1430)

### 19.1 Code Documentation (1381-1400)
- [ ] 1381. Add module-level doc comments to all modules
- [ ] 1382. Add doc comments to all public structs
- [ ] 1383. Add doc comments to all public functions
- [ ] 1384. Add doc comments to all public traits
- [ ] 1385. Add doc comments to all public enums
- [ ] 1386. Include examples in doc comments
- [ ] 1387. Add `# Examples` sections
- [ ] 1388. Add `# Errors` sections
- [ ] 1389. Add `# Panics` sections where applicable
- [ ] 1390. Document safety invariants
- [ ] 1391. Document performance characteristics
- [ ] 1392. Link related items with `[`/`]`
- [ ] 1393. Run `cargo doc` and fix warnings
- [ ] 1394. Add `#![deny(missing_docs)]` to lib.rs
- [ ] 1395. Generate and review HTML docs
- [ ] 1396. Ensure all public API is documented
- [ ] 1397. Add diagrams where helpful
- [ ] 1398. Document configuration options
- [ ] 1399. Document environment variables
- [ ] 1400. Document file formats

### 19.2 User Documentation (1401-1420)
- [ ] 1401. Create README.md for Rust project
- [ ] 1402. Add project description
- [ ] 1403. Add installation instructions
- [ ] 1404. Add build instructions
- [ ] 1405. Add usage examples
- [ ] 1406. Add configuration guide
- [ ] 1407. Add CLI reference
- [ ] 1408. Add troubleshooting section
- [ ] 1409. Add FAQ section
- [ ] 1410. Create CHANGELOG.md
- [ ] 1411. Document migration from Python version
- [ ] 1412. Document breaking changes
- [ ] 1413. Create CONTRIBUTING.md
- [ ] 1414. Add code style guidelines
- [ ] 1415. Add testing guidelines
- [ ] 1416. Add PR process
- [ ] 1417. Create LICENSE file
- [ ] 1418. Add architecture overview document
- [ ] 1419. Add development setup guide
- [ ] 1420. Add deployment guide

### 19.3 API Documentation (1421-1430)
- [ ] 1421. Set up docs.rs configuration
- [ ] 1422. Configure feature flags in docs
- [ ] 1423. Add API overview page
- [ ] 1424. Document public API stability
- [ ] 1425. Add version compatibility notes
- [ ] 1426. Document optional features
- [ ] 1427. Add usage tutorials
- [ ] 1428. Add integration examples
- [ ] 1429. Publish documentation
- [ ] 1430. Set up documentation hosting

---

## Phase 20: Migration & Cleanup (Items 1431-1500)

### 20.1 Feature Parity Verification (1431-1450)
- [ ] 1431. Create feature parity checklist
- [ ] 1432. Verify: config loading from TOML
- [ ] 1433. Verify: config loading from JSON (legacy)
- [ ] 1434. Verify: profile overlay support
- [ ] 1435. Verify: state management
- [ ] 1436. Verify: legacy state migration
- [ ] 1437. Verify: file hashing
- [ ] 1438. Verify: text extraction (TXT, PDF, DOCX)
- [ ] 1439. Verify: OCR support
- [ ] 1440. Verify: resume scoring
- [ ] 1441. Verify: job scoring
- [ ] 1442. Verify: match scoring
- [ ] 1443. Verify: iteration score
- [ ] 1444. Verify: iteration strategies
- [ ] 1445. Verify: recommendations
- [ ] 1446. Verify: schema validation
- [ ] 1447. Verify: output generation (JSON, TOML, TXT)
- [ ] 1448. Verify: job scraping
- [ ] 1449. Verify: saved searches
- [ ] 1450. Verify: all CLI commands

### 20.2 API Compatibility (1451-1465)
- [ ] 1451. Verify Gemini API integration
- [ ] 1452. Verify OpenAI API integration
- [ ] 1453. Verify Anthropic API integration
- [ ] 1454. Verify Llama API integration
- [ ] 1455. Test with real API calls
- [ ] 1456. Verify error handling matches Python
- [ ] 1457. Verify retry behavior
- [ ] 1458. Verify rate limiting
- [ ] 1459. Verify response parsing
- [ ] 1460. Verify prompt compatibility
- [ ] 1461. Test enhancement output format
- [ ] 1462. Test revision output format
- [ ] 1463. Test summarization output format
- [ ] 1464. Document any API differences
- [ ] 1465. Create migration notes for API changes

### 20.3 Data Format Compatibility (1466-1480)
- [ ] 1466. Verify config.toml compatibility
- [ ] 1467. Verify scoring_weights.toml compatibility
- [ ] 1468. Verify state file compatibility
- [ ] 1469. Verify saved_searches.toml compatibility
- [ ] 1470. Verify output JSON format compatibility
- [ ] 1471. Verify output TOML format compatibility
- [ ] 1472. Verify manifest.toml format
- [ ] 1473. Verify scores.toml format
- [ ] 1474. Test reading Python-generated files
- [ ] 1475. Test writing files readable by Python
- [ ] 1476. Document any format differences
- [ ] 1477. Create format migration tool if needed
- [ ] 1478. Test backward compatibility
- [ ] 1479. Test forward compatibility
- [ ] 1480. Add format version detection

### 20.4 Performance Comparison (1481-1490)
- [ ] 1481. Benchmark Rust vs Python: startup time
- [ ] 1482. Benchmark Rust vs Python: config loading
- [ ] 1483. Benchmark Rust vs Python: file hashing
- [ ] 1484. Benchmark Rust vs Python: text extraction
- [ ] 1485. Benchmark Rust vs Python: scoring
- [ ] 1486. Benchmark Rust vs Python: output generation
- [ ] 1487. Benchmark Rust vs Python: full pipeline
- [ ] 1488. Document performance improvements
- [ ] 1489. Document memory usage differences
- [ ] 1490. Create performance comparison report

### 20.5 Final Cleanup (1491-1500)
- [ ] 1491. Remove unused dependencies
- [ ] 1492. Run `cargo clippy` and fix all warnings
- [ ] 1493. Run `cargo fmt` on all code
- [ ] 1494. Run `cargo audit` and fix vulnerabilities
- [ ] 1495. Review and clean up TODO comments
- [ ] 1496. Review and clean up FIXME comments
- [ ] 1497. Ensure all tests pass
- [ ] 1498. Ensure all benchmarks run
- [ ] 1499. Final code review
- [ ] 1500. Tag release version

---

## Additional Items (1501+)

### Testing Edge Cases (1501-1520)
- [ ] 1501. Test with empty resume file
- [ ] 1502. Test with very large resume file (10MB+)
- [ ] 1503. Test with resume containing only images
- [ ] 1504. Test with corrupt PDF file
- [ ] 1505. Test with password-protected PDF
- [ ] 1506. Test with non-UTF8 text file
- [ ] 1507. Test with job description URL instead of file
- [ ] 1508. Test with network failure during API call
- [ ] 1509. Test with API rate limiting
- [ ] 1510. Test with invalid API key
- [ ] 1511. Test with expired API key
- [ ] 1512. Test with missing config file
- [ ] 1513. Test with corrupt config file
- [ ] 1514. Test with missing required config fields
- [ ] 1515. Test with invalid config values
- [ ] 1516. Test with read-only output directory
- [ ] 1517. Test with full disk
- [ ] 1518. Test with special characters in filenames
- [ ] 1519. Test with very long file paths
- [ ] 1520. Test with symlinks

### Error Messages & UX (1521-1540)
- [ ] 1521. Review all error messages for clarity
- [ ] 1522. Add context to error messages
- [ ] 1523. Add suggestions for fixing errors
- [ ] 1524. Ensure consistent error message format
- [ ] 1525. Add color coding to error severity
- [ ] 1526. Add progress indicators for long operations
- [ ] 1527. Add ETA for batch processing
- [ ] 1528. Add verbose mode output
- [ ] 1529. Add debug mode output
- [ ] 1530. Add quiet mode (suppress non-errors)
- [ ] 1531. Improve interactive menu layout
- [ ] 1532. Add keyboard shortcuts
- [ ] 1533. Add history for repeated operations
- [ ] 1534. Add confirmation prompts for destructive operations
- [ ] 1535. Add undo support where feasible
- [ ] 1536. Improve table formatting
- [ ] 1537. Add pagination for long lists
- [ ] 1538. Add search/filter for lists
- [ ] 1539. Improve help text formatting
- [ ] 1540. Add man page generation

### Logging & Monitoring (1541-1560)
- [ ] 1541. Implement structured logging
- [ ] 1542. Add log levels (trace, debug, info, warn, error)
- [ ] 1543. Add log rotation
- [ ] 1544. Add log file output option
- [ ] 1545. Add request/response logging for APIs
- [ ] 1546. Add timing logs for performance analysis
- [ ] 1547. Add metrics collection (optional)
- [ ] 1548. Add tracing support for debugging
- [ ] 1549. Add span tracking for operations
- [ ] 1550. Add error tracking integration (optional)
- [ ] 1551. Log configuration on startup
- [ ] 1552. Log environment info on startup
- [ ] 1553. Log version info on startup
- [ ] 1554. Add operation IDs for tracking
- [ ] 1555. Add correlation IDs for related operations
- [ ] 1556. Log state changes
- [ ] 1557. Log file operations
- [ ] 1558. Sanitize sensitive data in logs
- [ ] 1559. Add log sampling for high-volume events
- [ ] 1560. Document logging configuration

### Security (1561-1580)
- [ ] 1561. Review API key handling
- [ ] 1562. Ensure API keys never logged
- [ ] 1563. Use secure string types for secrets
- [ ] 1564. Clear secrets from memory when done
- [ ] 1565. Review file permission handling
- [ ] 1566. Set appropriate permissions on created files
- [ ] 1567. Validate all file paths for traversal attacks
- [ ] 1568. Sanitize user input in prompts
- [ ] 1569. Review dependency security
- [ ] 1570. Pin dependency versions
- [ ] 1571. Add security policy file
- [ ] 1572. Document security considerations
- [ ] 1573. Add input validation for all external data
- [ ] 1574. Add output encoding for all external data
- [ ] 1575. Review error messages for info leakage
- [ ] 1576. Add rate limiting for local operations
- [ ] 1577. Add resource limits (memory, file handles)
- [ ] 1578. Add timeout for all operations
- [ ] 1579. Review thread safety
- [ ] 1580. Add security audit to CI

### Platform Support (1581-1600)
- [ ] 1581. Test on Linux (Ubuntu)
- [ ] 1582. Test on Linux (Fedora)
- [ ] 1583. Test on Linux (Arch)
- [ ] 1584. Test on macOS (Intel)
- [ ] 1585. Test on macOS (Apple Silicon)
- [ ] 1586. Test on Windows 10
- [ ] 1587. Test on Windows 11
- [ ] 1588. Test on WSL
- [ ] 1589. Fix platform-specific path handling
- [ ] 1590. Fix platform-specific line endings
- [ ] 1591. Fix platform-specific permissions
- [ ] 1592. Add platform-specific defaults
- [ ] 1593. Document platform requirements
- [ ] 1594. Document platform-specific installation
- [ ] 1595. Create platform-specific packages
- [ ] 1596. Add Homebrew formula (macOS)
- [ ] 1597. Add apt package (Debian/Ubuntu)
- [ ] 1598. Add rpm package (Fedora/RHEL)
- [ ] 1599. Add Chocolatey package (Windows)
- [ ] 1600. Add Docker image

---

## Progress Summary

| Phase | Items | Completed | Percentage |
|-------|-------|-----------|------------|
| 1. Project Setup | 50 | 0 | 0% |
| 2. Error Handling | 70 | 0 | 0% |
| 3. Configuration | 100 | 0 | 0% |
| 4. State Management | 80 | 0 | 0% |
| 5. Utilities | 80 | 0 | 0% |
| 6. Scoring | 120 | 0 | 0% |
| 7. Agent/LLM | 100 | 0 | 0% |
| 8. Agent Registry | 50 | 0 | 0% |
| 9. Job Scraper | 100 | 0 | 0% |
| 10. Input Handler | 50 | 0 | 0% |
| 11. Output Generator | 80 | 0 | 0% |
| 12. Resume Processor | 80 | 0 | 0% |
| 13. Recommendations | 40 | 0 | 0% |
| 14. Schema Validation | 50 | 0 | 0% |
| 15. CLI Module | 100 | 0 | 0% |
| 16. TOML I/O | 50 | 0 | 0% |
| 17. Gemini Integrator | 80 | 0 | 0% |
| 18. Integration & Testing | 100 | 0 | 0% |
| 19. Documentation | 50 | 0 | 0% |
| 20. Migration & Cleanup | 70 | 0 | 0% |
| Additional Items | 100 | 0 | 0% |
| **TOTAL** | **1600** | **0** | **0%** |

---

## Notes

- Items are numbered sequentially for easy reference
- Each item should be marked with `[x]` when completed
- Some items may need to be split into sub-items during implementation
- Priority should generally follow phase order, but some items can be parallelized
- Dependencies between items should be respected
- Add new items as discovered during implementation

---

*Last Updated: 2026-01-20*
