import os
import unittest
from tempfile import TemporaryDirectory

from config import load_config


class TestConfigProfileOverlayLoading(unittest.TestCase):
    def test_profile_overlay_merge_order_defaults_profile_main(self):
        """
        Verifies merge order:
          defaults -> profile overlay -> main config

        Meaning:
          - profile can change defaults
          - main config can override profile
        """
        with TemporaryDirectory() as tmp:
            cfg_dir = os.path.join(tmp, "config")
            profiles_dir = os.path.join(cfg_dir, "profiles")
            os.makedirs(profiles_dir, exist_ok=True)

            profile_path = os.path.join(profiles_dir, "safe.toml")
            main_path = os.path.join(cfg_dir, "config.toml")

            # Profile sets iterate=true and target_score=90, and output_folder to "workspace/profile_out".
            with open(profile_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(
                    "\n".join(
                        [
                            "[processing]",
                            "iterate_until_score_reached = true",
                            "target_score = 90.0",
                            "max_concurrent_requests = 3",
                            "",
                            "[paths]",
                            'output_folder = "workspace/profile_out"',
                            "",
                        ]
                    )
                    + "\n"
                )

            # Main config overrides target_score and max_concurrent_requests but keeps iterate=true from profile.
            with open(main_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(
                    "\n".join(
                        [
                            "[profile]",
                            # IMPORTANT: relative to the main config file directory
                            'file = "profiles/safe.toml"',
                            "",
                            "[processing]",
                            "target_score = 80.0",
                            "max_concurrent_requests = 1",
                            "",
                            # Override output folder again from main config
                            "[paths]",
                            'output_folder = "workspace/main_out"',
                            "",
                        ]
                    )
                    + "\n"
                )

            cfg = load_config(config_file_path=main_path, cli_args=None)

            # From profile
            self.assertTrue(cfg.iterate_until_score_reached)

            # Overridden by main
            self.assertEqual(cfg.target_score, 80.0)
            self.assertEqual(cfg.max_concurrent_requests, 1)

            # output_folder should come from main config (normalized absolute)
            self.assertTrue(
                cfg.output_folder.endswith(os.path.join("workspace", "main_out"))
            )

    def test_profile_not_applied_when_missing(self):
        """
        If the profile file path doesn't exist, it should be ignored (best-effort),
        and the main config should still load.
        """
        with TemporaryDirectory() as tmp:
            cfg_dir = os.path.join(tmp, "config")
            os.makedirs(cfg_dir, exist_ok=True)

            main_path = os.path.join(cfg_dir, "config.toml")

            with open(main_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(
                    "\n".join(
                        [
                            "[profile]",
                            'file = "profiles/does_not_exist.toml"',
                            "",
                            "[processing]",
                            "target_score = 77.0",
                            "",
                        ]
                    )
                    + "\n"
                )

            cfg = load_config(config_file_path=main_path, cli_args=None)

            self.assertEqual(cfg.target_score, 77.0)
            # Ensure config loads and returns a Config object with expected attribute
            self.assertTrue(hasattr(cfg, "num_versions_per_job"))

    def test_profile_path_resolves_relative_to_main_config_directory(self):
        """
        The overlay resolver should treat a relative profile path as relative to the directory
        containing the main config file (not necessarily the current working directory).
        """
        with TemporaryDirectory() as tmp:
            nested = os.path.join(tmp, "nested", "cfg")
            profiles_dir = os.path.join(nested, "profiles")
            os.makedirs(profiles_dir, exist_ok=True)

            profile_path = os.path.join(profiles_dir, "p.toml")
            main_path = os.path.join(nested, "config.toml")

            with open(profile_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(
                    "\n".join(
                        [
                            "[processing]",
                            "max_concurrent_requests = 4",
                            "",
                        ]
                    )
                    + "\n"
                )

            with open(main_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(
                    "\n".join(
                        [
                            "[profile]",
                            'file = "profiles/p.toml"',
                            "",
                            # do not override max_concurrent_requests here; should come from profile
                        ]
                    )
                    + "\n"
                )

            cfg = load_config(config_file_path=main_path, cli_args=None)
            self.assertEqual(cfg.max_concurrent_requests, 4)

    def test_profile_loaded_only_for_toml_main_config(self):
        """
        The profile overlay mechanism is intended for TOML configs. If main config is JSON,
        profile overlay is not applicable. However, since the loader maps JSON into TOML-shape,
        we at least verify JSON loads without requiring profile fields.
        """
        with TemporaryDirectory() as tmp:
            json_cfg_path = os.path.join(tmp, "config.json")
            with open(json_cfg_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(
                    "\n".join(
                        [
                            "{",
                            '  "output_folder": "workspace/json_out",',
                            '  "num_versions_per_job": 2,',
                            '  "model_name": "gemini-pro"',
                            "}",
                        ]
                    )
                    + "\n"
                )

            cfg = load_config(config_file_path=json_cfg_path, cli_args=None)
            self.assertTrue(
                cfg.output_folder.endswith(os.path.join("workspace", "json_out"))
            )
            self.assertEqual(cfg.num_versions_per_job, 2)

    def test_main_config_overrides_profile_for_paths_and_processing(self):
        """
        Spot-check multiple keys to ensure main config wins over profile for both [paths] and [processing].
        """
        with TemporaryDirectory() as tmp:
            cfg_dir = os.path.join(tmp, "config")
            profiles_dir = os.path.join(cfg_dir, "profiles")
            os.makedirs(profiles_dir, exist_ok=True)

            profile_path = os.path.join(profiles_dir, "overlay.toml")
            main_path = os.path.join(cfg_dir, "config.toml")

            with open(profile_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(
                    "\n".join(
                        [
                            "[paths]",
                            'job_search_results_folder = "workspace/profile_results"',
                            "",
                            "[processing]",
                            'structured_output_format = "json"',
                            "write_manifest_file = false",
                            "",
                        ]
                    )
                    + "\n"
                )

            with open(main_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(
                    "\n".join(
                        [
                            "[profile]",
                            'file = "profiles/overlay.toml"',
                            "",
                            "[paths]",
                            'job_search_results_folder = "workspace/main_results"',
                            "",
                            "[processing]",
                            'structured_output_format = "toml"',
                            "write_manifest_file = true",
                            "",
                        ]
                    )
                    + "\n"
                )

            cfg = load_config(config_file_path=main_path, cli_args=None)

            self.assertTrue(
                cfg.job_search_results_folder.endswith(
                    os.path.join("workspace", "main_results")
                )
            )
            self.assertEqual(cfg.structured_output_format, "toml")
            self.assertTrue(cfg.write_manifest_file)


if __name__ == "__main__":
    unittest.main()
