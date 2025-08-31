import argparse
import json
import os

class Config:
    def __init__(self,
                 output_folder="output",
                 num_versions_per_job=3,
                 model_name="gemini-pro",
                 temperature=0.7,
                 top_p=0.95,
                 top_k=40,
                 max_output_tokens=8192,
                 input_resumes_folder="input_resumes",
                 job_descriptions_folder="job_descriptions"):
        # Normalize folder paths to handle both relative and absolute paths
        self.output_folder = os.path.abspath(output_folder)
        self.num_versions_per_job = num_versions_per_job
        self.model_name = model_name
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
        self.max_output_tokens = max_output_tokens
        self.input_resumes_folder = os.path.abspath(input_resumes_folder)
        self.job_descriptions_folder = os.path.abspath(job_descriptions_folder)

    def to_dict(self):
        return {
            "output_folder": self.output_folder,
            "num_versions_per_job": self.num_versions_per_job,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "max_output_tokens": self.max_output_tokens,
            "input_resumes_folder": self.input_resumes_folder,
            "job_descriptions_folder": self.job_descriptions_folder
        }

def load_config(config_file_path="config.json", cli_args=None):
    # Default configuration
    config_data = {
        "output_folder": "output",
        "num_versions_per_job": 3,
        "model_name": "gemini-pro",
        "temperature": 0.7,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "input_resumes_folder": "input_resumes",
        "job_descriptions_folder": "job_descriptions"
    }

    # Load configuration from file if it exists
    if os.path.exists(config_file_path):
        with open(config_file_path, 'r') as f:
            file_config = json.load(f)
            config_data.update(file_config) # Override defaults with file settings

    # Override with CLI arguments if provided
    if cli_args:
        for key, value in vars(cli_args).items():
            if value is not None and key in config_data:
                config_data[key] = value

    # Normalize folder paths to handle both relative and absolute paths
    return Config(
        output_folder=os.path.abspath(config_data["output_folder"]),
        num_versions_per_job=config_data["num_versions_per_job"],
        model_name=config_data["model_name"],
        temperature=config_data["temperature"],
        top_p=config_data["top_p"],
        top_k=config_data["top_k"],
        max_output_tokens=config_data["max_output_tokens"],
        input_resumes_folder=os.path.abspath(config_data["input_resumes_folder"]),
        job_descriptions_folder=os.path.abspath(config_data["job_descriptions_folder"])
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ATS Checker Configuration Example")
    parser.add_argument("--config_file", type=str, default="config.json",
                        help="Path to the configuration JSON file.")
    parser.add_argument("--output_folder", type=str, help="Folder to save generated output.")
    parser.add_argument("--num_versions_per_job", type=int, help="Number of resume versions to generate per job description.")
    parser.add_argument("--model_name", type=str, help="Name of the generative AI model to use.")
    parser.add_argument("--temperature", type=float, help="Controls the randomness of the output.")
    parser.add_argument("--top_p", type=float, help="The maximum cumulative probability of tokens to consider.")
    parser.add_argument("--top_k", type=int, help="The maximum number of tokens to consider.")
    parser.add_argument("--max_output_tokens", type=int, help="The maximum number of tokens to generate.")
    parser.add_argument("--input_resumes_folder", type=str, help="Folder containing input resume JSON files.")
    parser.add_argument("--job_descriptions_folder", type=str, help="Folder containing job description text files.")
    
    args = parser.parse_args()

    config = load_config(config_file_path=args.config_file, cli_args=args)
    print("Loaded Configuration:")
    for key, value in config.to_dict().items():
        print(f"  {key}: {value}")

    # Example with a config file (create a dummy config.json for testing)
    # with open("my_config.json", "w") as f:
    #     json.dump({"output_folder": "file_output", "num_versions_per_job": 2}, f)
    # config_from_file = load_config(config_file_path="my_config.json")
    # print("\nLoaded Configuration from file:")
    # for key, value in config_from_file.to_dict().items():
    #     print(f"  {key}: {value}")
    # os.remove("my_config.json") # Clean up dummy file