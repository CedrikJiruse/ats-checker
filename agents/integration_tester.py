"""
Integration & Pipeline Tester Agent

Validates the complete end-to-end workflow: input → enhancement → scoring → iteration → output.
Tests with sample data to catch integration breaks, missing dependencies, and configuration issues.

Usage:
    python -m agents.integration_tester --mode full
    python -m agents.integration_tester --mode quick
    python -m agents.integration_tester --mode api-only
    python -m agents.integration_tester --cleanup
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Single test result"""
    name: str
    passed: bool
    duration: float
    error: Optional[str] = None
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


@dataclass
class TestSuite:
    """Collection of test results"""
    name: str
    results: List[TestResult]

    @property
    def passed_count(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed_count(self) -> int:
        return len(self.results) - self.passed_count

    @property
    def total_time(self) -> float:
        return sum(r.duration for r in self.results)

    def summary(self) -> str:
        return (
            f"{self.name}: {self.passed_count}/{len(self.results)} passed "
            f"({self.total_time:.2f}s)"
        )


class SampleDataGenerator:
    """Generates realistic test data for integration testing"""

    @staticmethod
    def sample_resume() -> str:
        """Generate a sample resume in text format"""
        return """JOHN DOE
john.doe@example.com | 555-0123 | linkedin.com/in/johndoe | github.com/johndoe

SUMMARY
Experienced software engineer with 5+ years of full-stack development expertise.
Proficient in Python, JavaScript, and cloud technologies. Strong track record of
delivering scalable solutions and mentoring junior developers.

EXPERIENCE
Senior Software Engineer
Tech Innovations Inc., San Francisco, CA
January 2022 - Present
• Led microservices architecture redesign, improving API response time by 40%
• Mentored 3 junior developers, conducting weekly code reviews
• Implemented CI/CD pipeline using Jenkins and Docker, reducing deployment time by 60%
• Architected real-time data processing system handling 1M+ events/day using Apache Kafka

Software Engineer
Digital Solutions Corp., New York, NY
June 2019 - December 2021
• Developed RESTful APIs using Python Flask, serving 10K+ daily users
• Built responsive frontend using React and Redux, increasing user engagement by 35%
• Contributed to open-source projects (200+ GitHub stars)
• Optimized database queries, reducing query time by 50%

EDUCATION
Master of Science in Computer Science
University of Technology, Boston, MA
Graduated: May 2019 | GPA: 3.8/4.0

Bachelor of Science in Software Engineering
State University, Austin, TX
Graduated: May 2017 | GPA: 3.7/4.0

SKILLS
Languages: Python, JavaScript, TypeScript, SQL, Java
Frameworks: Django, Flask, React, Node.js, FastAPI
Cloud: AWS (EC2, S3, Lambda), Google Cloud Platform, Docker, Kubernetes
Tools: Git, Jenkins, Terraform, Elasticsearch, PostgreSQL, Redis
"""

    @staticmethod
    def sample_job_description() -> str:
        """Generate a sample job description"""
        return """Senior Software Engineer - Backend

Location: San Francisco, CA (Remote Available)
Salary: $180K - $220K

ABOUT THE ROLE
We're looking for a Senior Backend Engineer to help us build the next generation
of our platform. You'll work on microservices, APIs, and real-time systems that
power our product for thousands of users.

RESPONSIBILITIES
• Design and implement scalable backend services using Python or Go
• Lead architectural decisions and mentor junior engineers
• Optimize database performance and ensure high availability
• Collaborate with frontend teams on API design
• Participate in code reviews and technical planning

REQUIREMENTS
• 5+ years of software engineering experience
• Strong proficiency in Python, Go, or Java
• Experience with microservices and distributed systems
• Proficiency with PostgreSQL or similar relational databases
• Experience with AWS or GCP
• Strong communication and mentoring skills

NICE TO HAVE
• Experience with Kubernetes and Docker
• Familiarity with event-driven architecture
• Open source contributions
• Experience with real-time systems

BENEFITS
• Competitive salary and equity
• Health insurance and 401k
• Remote work options
• Professional development budget
• Flexible work hours
"""

    @staticmethod
    def sample_resume_json() -> Dict[str, Any]:
        """Generate a sample enhanced resume in JSON format"""
        return {
            "personal_info": {
                "name": "John Doe",
                "email": "john.doe@example.com",
                "phone": "555-0123",
                "linkedin": "linkedin.com/in/johndoe",
                "github": "github.com/johndoe"
            },
            "summary": "Experienced software engineer with 5+ years of full-stack development expertise.",
            "experience": [
                {
                    "title": "Senior Software Engineer",
                    "company": "Tech Innovations Inc.",
                    "location": "San Francisco, CA",
                    "start_date": "2022-01-01",
                    "end_date": "Present",
                    "description": [
                        "Led microservices architecture redesign, improving API response time by 40%",
                        "Mentored 3 junior developers with weekly code reviews",
                        "Implemented CI/CD pipeline using Jenkins and Docker"
                    ]
                }
            ],
            "education": [
                {
                    "degree": "M.Sc. Computer Science",
                    "institution": "University of Technology",
                    "location": "Boston, MA",
                    "graduation_date": "2019-05-01",
                    "gpa": "3.8/4.0"
                }
            ],
            "skills": ["Python", "JavaScript", "React", "Docker", "AWS", "PostgreSQL"],
            "projects": [
                {
                    "name": "Real-time Data Pipeline",
                    "description": "Built Kafka-based system processing 1M+ events/day",
                    "link": "github.com/johndoe/realtime-pipeline"
                }
            ]
        }


class IntegrationTester:
    """Main integration testing orchestrator"""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.temp_dir: Optional[Path] = None
        self.test_suites: List[TestSuite] = []

    def setup_temp_workspace(self) -> Path:
        """Create temporary workspace for testing"""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="ats_integration_test_"))
        logger.info(f"Created temporary workspace: {self.temp_dir}")

        # Create required directories
        (self.temp_dir / "input_resumes").mkdir(exist_ok=True)
        (self.temp_dir / "job_descriptions").mkdir(exist_ok=True)
        (self.temp_dir / "output").mkdir(exist_ok=True)
        (self.temp_dir / "job_search_results").mkdir(exist_ok=True)
        (self.temp_dir / "data").mkdir(exist_ok=True)

        return self.temp_dir

    def cleanup_temp_workspace(self) -> None:
        """Remove temporary workspace"""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            logger.info(f"Cleaned up temporary workspace: {self.temp_dir}")

    def test_config_loading(self) -> TestResult:
        """Test configuration loading and validation"""
        import time
        start = time.time()

        try:
            from config import load_config

            config = load_config(config_file_path="config/config.toml")

            # Validate critical config attributes
            assert config.output_folder, "output_folder not set"
            assert config.input_resumes_folder, "input_resumes_folder not set"
            assert config.model_name, "model_name not set"
            assert config.max_iterations >= 0, "max_iterations invalid"
            assert config.target_score >= 0, "target_score invalid"
            assert isinstance(config.ai_agents, dict), "ai_agents not a dict"

            return TestResult(
                name="config_loading",
                passed=True,
                duration=time.time() - start,
                details={
                    "output_folder": config.output_folder,
                    "model_name": config.model_name,
                    "agents": list(config.ai_agents.keys())
                }
            )
        except Exception as e:
            return TestResult(
                name="config_loading",
                passed=False,
                duration=time.time() - start,
                error=str(e)
            )

    def test_state_manager(self) -> TestResult:
        """Test state management"""
        import time
        start = time.time()

        try:
            from state_manager import StateManager
            import tempfile

            # Use temp dir if available, otherwise create one
            if self.temp_dir:
                state_file = self.temp_dir / "test_state.toml"
            else:
                state_file = Path(tempfile.gettempdir()) / "ats_test_state.toml"

            manager = StateManager(str(state_file))

            # Test update and retrieval
            test_hash = "abc123"
            test_path = "/path/to/output.json"
            manager.update_resume_state(test_hash, test_path)

            # Reload and verify
            manager2 = StateManager(str(state_file))
            retrieved = manager2.get_resume_state(test_hash)
            # Retrieved is a dict with 'output_path' key
            if isinstance(retrieved, dict):
                retrieved_path = retrieved.get("output_path")
            else:
                retrieved_path = retrieved
            assert retrieved_path == test_path, f"State mismatch: {retrieved_path} != {test_path}"

            return TestResult(
                name="state_manager",
                passed=True,
                duration=time.time() - start,
                details={"state_file": str(state_file)}
            )
        except Exception as e:
            return TestResult(
                name="state_manager",
                passed=False,
                duration=time.time() - start,
                error=str(e)
            )

    def test_input_handler(self) -> TestResult:
        """Test input file handling"""
        import time
        start = time.time()

        try:
            from input_handler import InputHandler
            from state_manager import StateManager

            state_manager = StateManager(str(self.temp_dir / "state.toml"))
            handler = InputHandler(state_manager)

            # Create test resume file
            resume_path = self.temp_dir / "input_resumes" / "test_resume.txt"
            resume_path.write_text(SampleDataGenerator.sample_resume())

            # Test text extraction
            content = handler.extract_text_from_file(str(resume_path))
            assert content and len(content) > 100, "Resume content too short"
            assert "EXPERIENCE" in content or "experience" in content.lower(), "Missing experience section"

            return TestResult(
                name="input_handler",
                passed=True,
                duration=time.time() - start,
                details={"resume_size": len(content)}
            )
        except Exception as e:
            return TestResult(
                name="input_handler",
                passed=False,
                duration=time.time() - start,
                error=str(e)
            )

    def test_output_generator(self) -> TestResult:
        """Test output file generation"""
        import time
        start = time.time()

        try:
            from output_generator import OutputGenerator

            generator = OutputGenerator(
                output_folder=str(self.temp_dir / "output"),
                structured_output_format="json"
            )

            resume_json = json.dumps(SampleDataGenerator.sample_resume_json())

            # Generate text output
            txt_path = generator.generate_text_output(
                resume_json,
                "test_resume.txt",
                "Software_Engineer"
            )

            assert Path(txt_path).exists(), f"Output file not created: {txt_path}"
            content = Path(txt_path).read_text()
            assert len(content) > 0, "Output file is empty"

            # Generate JSON output
            json_path = generator.generate_json_output(
                resume_json,
                "test_resume.txt",
                "Software_Engineer"
            )

            assert Path(json_path).exists(), f"JSON file not created: {json_path}"

            return TestResult(
                name="output_generator",
                passed=True,
                duration=time.time() - start,
                details={
                    "txt_output": txt_path,
                    "json_output": json_path,
                    "txt_size": len(content)
                }
            )
        except Exception as e:
            return TestResult(
                name="output_generator",
                passed=False,
                duration=time.time() - start,
                error=str(e)
            )

    def test_scoring_system(self) -> TestResult:
        """Test scoring functionality"""
        import time
        start = time.time()

        try:
            from scoring import score_resume, score_match

            resume = SampleDataGenerator.sample_resume_json()
            job = {
                "title": "Senior Software Engineer",
                "company": "Tech Corp",
                "location": "San Francisco",
                "description": SampleDataGenerator.sample_job_description(),
                "url": "",
                "source": "test"
            }

            # Test resume scoring
            resume_report = score_resume(resume, weights_toml_path="config/scoring_weights.toml")
            assert resume_report.total >= 0, "Resume score invalid"
            assert len(resume_report.categories) > 0, "No scoring categories"

            # Test match scoring
            match_report = score_match(resume, job, weights_toml_path="config/scoring_weights.toml")
            assert match_report.total >= 0, "Match score invalid"

            return TestResult(
                name="scoring_system",
                passed=True,
                duration=time.time() - start,
                details={
                    "resume_score": round(resume_report.total, 2),
                    "match_score": round(match_report.total, 2),
                    "resume_categories": len(resume_report.categories),
                    "match_categories": len(match_report.categories)
                }
            )
        except Exception as e:
            return TestResult(
                name="scoring_system",
                passed=False,
                duration=time.time() - start,
                error=str(e)
            )

    def test_gemini_api_connection(self) -> TestResult:
        """Test Gemini API availability and configuration"""
        import time
        start = time.time()

        try:
            import os
            from gemini_integrator import GeminiAPIIntegrator

            # Check for API key
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                return TestResult(
                    name="gemini_api_connection",
                    passed=False,
                    duration=time.time() - start,
                    error="GEMINI_API_KEY environment variable not set"
                )

            # Initialize integrator
            integrator = GeminiAPIIntegrator(model_name="gemini-pro")

            # Try to get agent
            agent = integrator._get_agent("enhancer")
            assert agent is not None, "Enhancer agent not initialized"

            return TestResult(
                name="gemini_api_connection",
                passed=True,
                duration=time.time() - start,
                details={
                    "model": "gemini-pro",
                    "agents": integrator.registry.list()
                }
            )
        except Exception as e:
            return TestResult(
                name="gemini_api_connection",
                passed=False,
                duration=time.time() - start,
                error=str(e)
            )

    def test_concurrent_processing(self) -> TestResult:
        """Test concurrent resume processing capability"""
        import time
        start = time.time()

        try:
            from concurrent.futures import ThreadPoolExecutor
            import hashlib

            # Create multiple test resumes
            num_resumes = 3
            for i in range(num_resumes):
                resume_path = self.temp_dir / "input_resumes" / f"resume_{i}.txt"
                resume_path.write_text(
                    SampleDataGenerator.sample_resume().replace(
                        "John Doe", f"Person {i}"
                    )
                )

            # Test concurrent hashing (simulating concurrent processing)
            def hash_file(path: Path) -> str:
                return hashlib.sha256(path.read_bytes()).hexdigest()

            with ThreadPoolExecutor(max_workers=2) as executor:
                resume_paths = list((self.temp_dir / "input_resumes").glob("resume_*.txt"))
                hashes = list(executor.map(hash_file, resume_paths))

            assert len(hashes) == num_resumes, f"Not all files hashed: {len(hashes)} != {num_resumes}"
            assert len(set(hashes)) == num_resumes, "Some hashes are identical"

            return TestResult(
                name="concurrent_processing",
                passed=True,
                duration=time.time() - start,
                details={
                    "num_resumes": num_resumes,
                    "num_hashes": len(hashes)
                }
            )
        except Exception as e:
            return TestResult(
                name="concurrent_processing",
                passed=False,
                duration=time.time() - start,
                error=str(e)
            )

    def run_quick_tests(self) -> TestSuite:
        """Run quick sanity checks"""
        logger.info("Running QUICK test suite...")
        results = [
            self.test_config_loading(),
            self.test_state_manager(),
            self.test_scoring_system(),
        ]
        return TestSuite(name="Quick Tests", results=results)

    def run_full_tests(self) -> TestSuite:
        """Run complete integration tests"""
        logger.info("Running FULL test suite...")
        self.setup_temp_workspace()

        try:
            results = [
                self.test_config_loading(),
                self.test_state_manager(),
                self.test_input_handler(),
                self.test_output_generator(),
                self.test_scoring_system(),
                self.test_gemini_api_connection(),
                self.test_concurrent_processing(),
            ]
            return TestSuite(name="Full Integration Tests", results=results)
        finally:
            self.cleanup_temp_workspace()

    def run_api_only_tests(self) -> TestSuite:
        """Test only API connectivity"""
        logger.info("Running API-ONLY test suite...")
        results = [
            self.test_config_loading(),
            self.test_gemini_api_connection(),
        ]
        return TestSuite(name="API-Only Tests", results=results)

    def print_results(self, suites: List[TestSuite]) -> int:
        """Print test results and return exit code"""
        # Use ASCII symbols for Windows compatibility
        is_windows = sys.platform == "win32"
        pass_symbol = "[PASS]" if is_windows else "✓ PASS"
        fail_symbol = "[FAIL]" if is_windows else "✗ FAIL"
        arrow = "->" if is_windows else "→"

        print("\n" + "=" * 80)
        print("INTEGRATION TEST RESULTS")
        print("=" * 80)

        total_passed = 0
        total_failed = 0

        for suite in suites:
            print(f"\n{suite.summary()}")
            print("-" * 80)

            for result in suite.results:
                status = pass_symbol if result.passed else fail_symbol
                print(f"{status:8} | {result.name:30} | {result.duration:7.2f}s")

                if result.details:
                    for key, value in result.details.items():
                        print(f"         | {arrow} {key}: {value}")

                if result.error:
                    print(f"         | ERROR: {result.error}")

                if result.passed:
                    total_passed += 1
                else:
                    total_failed += 1

        print("\n" + "=" * 80)
        print(f"SUMMARY: {total_passed} passed, {total_failed} failed")
        print("=" * 80 + "\n")

        return 0 if total_failed == 0 else 1


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Integration & Pipeline Tester Agent"
    )
    parser.add_argument(
        "--mode",
        choices=["quick", "full", "api-only"],
        default="quick",
        help="Test mode to run"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clean up any leftover test artifacts and exit"
    )

    args = parser.parse_args()

    tester = IntegrationTester()

    if args.cleanup:
        # This would be called after a test failure to clean up
        logger.info("Cleanup requested (no-op for now)")
        return 0

    try:
        if args.mode == "quick":
            suites = [tester.run_quick_tests()]
        elif args.mode == "full":
            suites = [tester.run_full_tests()]
        elif args.mode == "api-only":
            suites = [tester.run_api_only_tests()]

        return tester.print_results(suites)
    except Exception as e:
        logger.error(f"Test execution failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
