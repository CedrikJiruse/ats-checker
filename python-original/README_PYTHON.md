# ATS Resume Checker

An intelligent resume optimization tool that enhances resumes using AI (Google Gemini API), scores them against job descriptions, and helps you land interviews through iterative improvement.

## Features

### 🤖 AI-Powered Resume Enhancement
- **Restructuring**: Converts raw resumes (TXT, PDF, DOCX, images) into optimized JSON format using Google Gemini API
- **Multi-agent support**: Configurable AI agents for different tasks (enhancement, revision, scoring, summarization)
- **Iterative improvement**: Automatically revises resumes until target score is reached

### 📊 Comprehensive Scoring System
- **Resume quality score**: Evaluates structure, keywords, and impact
- **Job match score**: Compares resume against job description
- **Category breakdowns**: Detailed scoring for keywords, skills, alignment, etc.
- **Configurable weights**: Adjust scoring priorities via TOML configuration

### 🔍 Job Search & Scraping
- **Multi-site scraping**: Search LinkedIn, Indeed, Glassdoor, Google Jobs, ZipRecruiter via JobSpy
- **Advanced filtering**: Keywords, location, job type, remote-only, experience level, date posted, salary range
- **Configurable defaults**: Set location and other defaults to avoid repeated entry
- **Saved searches**: Store and re-run searches, track results with scoring

### 📝 Flexible Input/Output
- **Multiple formats**: Support for TXT, PDF, DOCX, images (with OCR)
- **Structured output**: TOML, JSON, or both
- **Human-readable text**: Clean TXT files with scoring breakdown and recommendations
- **Artifact files**: Manifest and score summary for tracking

### ⚙️ Configuration-Driven
- **TOML-based config**: Primary config file with profile overlays
- **Presets**: Safe, aggressive, balanced profiles for different strategies
- **Per-folder settings**: Input resumes, job descriptions, output organization
- **Per-portal config**: Enable/disable job portals, set country for Indeed, customize display names

### 🎯 Advanced Features
- **Schema validation**: Optional JSON schema validation with retries
- **Recommendations**: AI-generated suggestions for resume improvement
- **State tracking**: Avoid reprocessing via content hash tracking
- **Concurrent processing**: Parallel resume enhancement for speed
- **Score caching**: Optional caching to avoid redundant scoring

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd ats-checker

# Install dependencies
pip install -r requirements.txt

# Set up Google Gemini API
export GEMINI_API_KEY="your-api-key-here"
```

### Basic Usage

```bash
# Interactive mode (recommended)
python main.py

# Or with custom config
python main.py --config_file config/my-config.toml

# Batch mode with job description
python main.py --job_description "path/to/job.txt"

# Use a profile overlay
python main.py --profile aggressive
```

### Interactive Menu

```
1. Process resumes (all/with job/specific)
2. Convert files to standard format
3. Job search & scraping
4. View/edit settings
5. View available files
6. View generated outputs
7. Test OCR functionality
```

## Configuration

### Default Locations

```
workspace/
├── input_resumes/           # Put resumes here
├── job_descriptions/        # Put job descriptions here
├── output/                  # Generated outputs
└── job_search_results/      # Job search results

data/
├── processed_resumes_state.toml
└── saved_searches.toml

config/
├── config.toml             # Main configuration
├── scoring_weights.toml    # Scoring category weights
└── profiles/               # Configuration presets
    ├── safe.toml
    ├── aggressive.toml
    └── balanced.toml
```

### Job Search Defaults

Add defaults to avoid repeated entry:

```toml
[job_search.defaults]
location = "Dublin, Ireland"
keywords = "software engineer"
remote_only = false
date_posted = "week"
job_type = ["Full-time"]
experience_level = ["Mid", "Senior"]
```

### Portal Configuration

Enable/disable job portals or customize display names:

```toml
[job_search.portals.linkedin]
enabled = true
display_name = "LinkedIn"

[job_search.portals.indeed]
enabled = true
display_name = "Indeed"

[job_search.portals.glassdoor]
enabled = false  # Disable if not needed
```

### Processing Settings

```toml
[processing]
# Resume enhancement
num_versions_per_job = 1

# Iterative improvement
iterate_until_score_reached = true
target_score = 75.0
max_iterations = 5
iteration_strategy = "best_of"  # best_of, first_hit, patience

# Output format
structured_output_format = "both"  # json, toml, or both

# Optional features
schema_validation_enabled = true
recommendations_enabled = true
```

See `CLAUDE.md` for comprehensive configuration documentation.

## Usage Examples

### Process All Resumes

```bash
python main.py
# Select: 1 (Process all resumes)
```

### Process Resumes Against Specific Job

```bash
python main.py --job_description "Software Engineer.txt"
```

### Score a Resume

```bash
python main.py score-resume \
  --resume output/path/to/resume.json \
  --weights config/scoring_weights.toml
```

### Search Jobs

```bash
python main.py
# Select: 3 (Job search & scraping)
# Select: 1 (New job search)
# Choose portal(s), enter criteria
# Results saved and scored automatically
```

### View Results

```bash
python main.py
# Select: 6 (View generated outputs)
# or check workspace/output/
```

## Architecture

### Main Data Flow

```
Raw Resume (TXT/PDF/DOCX/Image)
    ↓
[Input Handler] - Extract text, handle OCR
    ↓
[Gemini Integration] - Enhance to JSON format
    ↓
[Schema Validation] - Validate JSON (optional)
    ↓
[Scoring] - Resume quality + job match
    ↓
[Iteration] - Revise until target (optional)
    ↓
[Output Generator] - Generate TOML/JSON/TXT files
    ↓
[State Manager] - Track processed resumes
    ↓
Output Files + Artifacts
```

### Key Modules

- **`main.py`**: Interactive CLI menu and entry point
- **`config.py`**: TOML-based configuration management with profiles
- **`resume_processor.py`**: Main processing pipeline orchestrator
- **`gemini_integrator.py`**: Multi-agent AI interface
- **`job_scraper_manager.py`**: Job scraping coordination
- **`scoring.py`**: Multi-dimensional scoring system
- **`output_generator.py`**: Structured and text output generation
- **`state_manager.py`**: Persistent state tracking (hash-based)

## Testing

```bash
# Run all tests
python -m pytest -q

# Run specific test file
python -m pytest tests/test_job_scrapers.py -v

# Run with coverage
python -m pytest --cov=. tests/
```

Test files:
- `tests/test_job_scrapers.py` - Job scraping and data structures
- `tests/test_config_profiles.py` - Configuration loading
- `tests/test_resume_processor.py` - Processing pipeline
- `tests/test_output_generator.py` - Output generation

## Configuration Profiles

### Safe Profile
Conservative settings, lower risk, slower processing:
```bash
python main.py --profile safe
```

### Aggressive Profile
High iteration, multiple versions, aggressive optimization:
```bash
python main.py --profile aggressive
```

### Balanced Profile
Default balanced approach between speed and quality.

See `config/profiles/` for all available profiles.

## API Requirements

### Google Gemini API

1. **Get API Key**: https://ai.google.dev/
2. **Set environment variable**:
   ```bash
   export GEMINI_API_KEY="your-key-here"
   ```
3. **Configure in code** (if needed):
   ```python
   from config import load_config
   config = load_config()
   # Uses GEMINI_API_KEY from environment
   ```

### JobSpy for Job Scraping (Optional)

```bash
pip install python-jobspy
```

Note: Heavy dependencies (numpy, pandas). Tests use mocks to avoid importing during test discovery.

## OCR Support (Optional)

For processing image resumes:

```bash
# Install Tesseract (system dependency)
# Windows: https://github.com/UB-Mannheim/tesseract/wiki
# macOS: brew install tesseract
# Linux: sudo apt-get install tesseract-ocr

# Then install Python wrapper
pip install pytesseract pillow

# Test it
python main.py
# Select: 7 (Test OCR functionality)
```

## Output Structure

Each processed resume generates:

```
output/
└── Resume_Name/
    └── Job_Title/
        └── 20240115_120345/
            ├── Resume_Name_Job_Title_enhanced.toml
            ├── Resume_Name_Job_Title_enhanced.json
            ├── Resume_Name_Job_Title_enhanced.txt
            ├── scores.toml
            └── manifest.toml
```

**Files explained:**
- `.toml/.json` - Structured resume data
- `.txt` - Human-readable format with scores
- `scores.toml` - Scoring breakdown
- `manifest.toml` - Metadata about processing run

## Performance Tips

1. **Parallel processing**: Increase `max_concurrent_requests` for faster multi-resume processing
2. **Score caching**: Enable `score_cache_enabled` to avoid redundant scoring
3. **Batch job searches**: Use "Search all sites" to scrape multiple portals in one go
4. **Profile selection**: Use `safe` profile for quick tests, `aggressive` for important applications

## Troubleshooting

### "No API key found"
```bash
export GEMINI_API_KEY="your-key-here"
python main.py
```

### "Tesseract not found"
```bash
# Reinstall Tesseract and add to PATH
# Then run:
python main.py
# Select: 7 (Test OCR functionality)
```

### "Output folder not writable"
- Check permissions on `workspace/output/`
- Ensure disk is not full
- Application will report the exact error

### Tests failing
```bash
# Make sure dependencies are installed
pip install -r requirements.txt

# Run tests with verbose output
python -m pytest tests/ -v
```

## Development

### Adding a New Job Portal

1. Create scraper class in `job_scrapers_improved.py`:
   ```python
   class MyPortalJobSpyScraper(JobSpyScraper):
       def __init__(self):
           super().__init__("myportal")
   ```

2. Add to config defaults in `config.py`
3. Update `job_scraper_manager.py` PORTAL_SCRAPERS
4. Add to `config/config.toml`:
   ```toml
   [job_search.portals.myportal]
   enabled = true
   display_name = "My Portal"
   ```

### Adding a New Scoring Category

1. Define in `config/scoring_weights.toml`
2. Implement scoring logic in `scoring.py`
3. Update `scoring.py` constants

### Configuration Changes

1. Update `config/config.toml` with new settings
2. Add defaults to `DEFAULTS` dict in `config.py`
3. Add fields to `Config` dataclass
4. Parse in `_build_config()` function

## Documentation

- **`CLAUDE.md`** - Comprehensive project documentation
- **`CODE_REVIEW.md`** - Code review findings and improvements
- **`docs/`** - Additional guides and specifications
- **`config/profiles/`** - Example configuration profiles

## License

See LICENSE file for details.

## Support

For issues, questions, or contributions:

1. Check `CLAUDE.md` for detailed documentation
2. Review `CODE_REVIEW.md` for known issues
3. Run tests: `python -m pytest -q`
4. Check git logs: `git log --oneline -10`

## Changelog

See git history for detailed changes:
```bash
git log --oneline
```

Recent major features:
- Job search defaults and portal configuration
- Multi-dimensional scoring system
- Iterative resume improvement
- Configuration profiles
- State tracking to avoid reprocessing
- OCR support for image resumes
