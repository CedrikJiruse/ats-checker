import os
import logging
import argparse
import json
from resume_processor import ResumeProcessor
from config import load_config, Config
from input_handler import InputHandler # Import InputHandler
from state_manager import StateManager # Import StateManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def display_menu():
    """Display the main menu options"""
    print("\n" + "="*50)
    print("           ATS Resume Checker")
    print("="*50)
    print("1. Process resumes")
    print("2. View/Edit settings")
    print("3. View available files")
    print("4. View generated outputs")
    print("5. Test OCR functionality")
    print("6. Exit")
    print("="*50)

def process_resumes_menu(config):
    """Handle resume processing options"""
    while True:
        print("\n--- Process Resumes ---")
        print("1. Process all resumes without tailoring")
        print("2. Process resumes tailored to a job description")
        print("3. Process a specific resume with a job description")
        print("4. Back to main menu")
        
        choice = input("Enter your choice (1-4): ").strip()
        
        if choice == "1":
            process_all_resumes(config)
        elif choice == "2":
            process_resumes_with_job_description(config)
        elif choice == "3":
            process_specific_resume_with_job(config)
        elif choice == "4":
            break
        else:
            print("Invalid choice. Please try again.")

def process_all_resumes(config):
    """Process all resumes without tailoring"""
    try:
        state_manager = StateManager()
        input_handler = InputHandler(state_manager, job_description_folder=config.job_descriptions_folder)
        
        logging.info(f"Starting resume processing for input folder: {config.input_resumes_folder}")
        processor = ResumeProcessor(
            input_folder=config.input_resumes_folder,
            output_folder=config.output_folder,
            model_name=config.model_name,
            temperature=config.temperature,
            top_p=config.top_p,
            top_k=config.top_k,
            max_output_tokens=config.max_output_tokens,
            num_versions_per_job=config.num_versions_per_job,
            job_description_folder=config.job_descriptions_folder
        )
        processor.process_resumes()
        logging.info("Resume processing completed successfully.")
        input("\nPress Enter to continue...")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        input("\nPress Enter to continue...")

def process_resumes_with_job_description(config):
    """Process resumes tailored to a specific job description"""
    # Get available job descriptions
    try:
        state_manager = StateManager()
        input_handler = InputHandler(state_manager, job_description_folder=config.job_descriptions_folder)
        job_descriptions = input_handler.get_job_descriptions()
        
        if not job_descriptions:
            print("No job descriptions found.")
            input("\nPress Enter to continue...")
            return
        
        print("\nAvailable job descriptions:")
        job_desc_list = list(job_descriptions.keys())
        for i, jd in enumerate(job_desc_list, 1):
            print(f"{i}. {jd}")
        
        choice = input("\nEnter the number of the job description to use: ").strip()
        if not choice.isdigit() or int(choice) < 1 or int(choice) > len(job_desc_list):
            print("Invalid choice.")
            input("\nPress Enter to continue...")
            return
        
        selected_jd = job_desc_list[int(choice) - 1]
        
        logging.info(f"Starting resume processing tailored to: {selected_jd}")
        processor = ResumeProcessor(
            input_folder=config.input_resumes_folder,
            output_folder=config.output_folder,
            model_name=config.model_name,
            temperature=config.temperature,
            top_p=config.top_p,
            top_k=config.top_k,
            max_output_tokens=config.max_output_tokens,
            num_versions_per_job=config.num_versions_per_job,
            job_description_folder=config.job_descriptions_folder
        )
        processor.process_resumes(job_description_name=selected_jd)
        logging.info("Resume processing completed successfully.")
        input("\nPress Enter to continue...")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        input("\nPress Enter to continue...")

def process_specific_resume_with_job(config):
    """Process a specific resume with a specific job description"""
    try:
        # Get available resumes
        if not os.path.exists(config.input_resumes_folder):
            print(f"Input folder '{config.input_resumes_folder}' does not exist.")
            input("\nPress Enter to continue...")
            return
        
        resume_files = [f for f in os.listdir(config.input_resumes_folder) if f.endswith(('.txt', '.md', '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'))]
        if not resume_files:
            print("No resume files found.")
            input("\nPress Enter to continue...")
            return
        
        print("\nAvailable resumes:")
        for i, resume in enumerate(resume_files, 1):
            print(f"{i}. {resume}")
        
        choice = input("\nEnter the number of the resume to process: ").strip()
        if not choice.isdigit() or int(choice) < 1 or int(choice) > len(resume_files):
            print("Invalid choice.")
            input("\nPress Enter to continue...")
            return
        
        selected_resume = resume_files[int(choice) - 1]
        resume_path = os.path.join(config.input_resumes_folder, selected_resume)
        
        # Get available job descriptions
        state_manager = StateManager()
        input_handler = InputHandler(state_manager, job_description_folder=config.job_descriptions_folder)
        job_descriptions = input_handler.get_job_descriptions()
        
        if not job_descriptions:
            print("No job descriptions found.")
            input("\nPress Enter to continue...")
            return
        
        print("\nAvailable job descriptions:")
        job_desc_list = list(job_descriptions.keys())
        for i, jd in enumerate(job_desc_list, 1):
            print(f"{i}. {jd}")
        
        jd_choice = input("\nEnter the number of the job description to use: ").strip()
        if not jd_choice.isdigit() or int(jd_choice) < 1 or int(jd_choice) > len(job_desc_list):
            print("Invalid choice.")
            input("\nPress Enter to continue...")
            return
        
        selected_jd = job_desc_list[int(jd_choice) - 1]
        
        # Process the specific resume
        logging.info(f"Processing resume '{selected_resume}' tailored to: {selected_jd}")
        
        # Read the resume content
        with open(resume_path, 'r', encoding='utf-8') as f:
            resume_content = f.read()
        
        # Create a temporary processor for this single resume
        processor = ResumeProcessor(
            input_folder=config.input_resumes_folder,
            output_folder=config.output_folder,
            model_name=config.model_name,
            temperature=config.temperature,
            top_p=config.top_p,
            top_k=config.top_k,
            max_output_tokens=config.max_output_tokens,
            num_versions_per_job=config.num_versions_per_job,
            job_description_folder=config.job_descriptions_folder
        )
        
        # Process just this one resume
        try:
            job_description_content = job_descriptions[selected_jd]
            for i in range(1, config.num_versions_per_job + 1):
                job_title_for_filename = selected_jd.replace('.txt', '').replace('.md', '')
                
                logging.info(f"Enhancing resume '{selected_resume}' with job description '{selected_jd}' (Version {i}).")
                
                enhanced_resume_data = processor.gemini_integrator.enhance_resume(resume_content, job_description=job_description_content)
                logging.info(f"Resume '{selected_resume}' enhanced by Gemini API (Version {i}).")
                
                text_output_path = processor.output_generator.generate_text_output(enhanced_resume_data, selected_resume, job_title_for_filename)
                logging.info(f"Generated TXT for '{selected_resume}' at: {text_output_path}")
            
            logging.info("Resume processing completed successfully.")
        except Exception as e:
            logging.error(f"Failed to process resume '{selected_resume}': {e}", exc_info=True)
        
        input("\nPress Enter to continue...")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        input("\nPress Enter to continue...")

def view_edit_settings(config, config_file_path):
    """View and edit application settings"""
    while True:
        print("\n--- Settings ---")
        print("Current configuration:")
        print(f"1. Output folder: {config.output_folder}")
        print(f"2. Number of versions per job: {config.num_versions_per_job}")
        print(f"3. Model name: {config.model_name}")
        print(f"4. Temperature: {config.temperature}")
        print(f"5. Top-p: {config.top_p}")
        print(f"6. Top-k: {config.top_k}")
        print(f"7. Max output tokens: {config.max_output_tokens}")
        print(f"8. Input resumes folder: {config.input_resumes_folder}")
        print(f"9. Job descriptions folder: {config.job_descriptions_folder}")
        print("10. Back to main menu")
        
        choice = input("\nEnter the number of the setting to edit (1-10): ").strip()
        
        if choice == "10":
            break
        elif choice in ["1", "2", "3", "4", "5", "6", "7", "8", "9"]:
            edit_setting(config, config_file_path, choice)
        else:
            print("Invalid choice. Please try again.")

def edit_setting(config, config_file_path, setting_choice):
    """Edit a specific setting"""
    setting_map = {
        "1": ("output_folder", "Output folder"),
        "2": ("num_versions_per_job", "Number of versions per job"),
        "3": ("model_name", "Model name"),
        "4": ("temperature", "Temperature"),
        "5": ("top_p", "Top-p"),
        "6": ("top_k", "Top-k"),
        "7": ("max_output_tokens", "Max output tokens"),
        "8": ("input_resumes_folder", "Input resumes folder"),
        "9": ("job_descriptions_folder", "Job descriptions folder")
    }
    
    if setting_choice in setting_map:
        key, name = setting_map[setting_choice]
        current_value = getattr(config, key)
        new_value = input(f"Enter new value for {name} (current: {current_value}): ").strip()
        
        if new_value:
            # Update config object
            if key in ["num_versions_per_job", "top_k", "max_output_tokens"]:
                try:
                    new_value = int(new_value)
                except ValueError:
                    print("Invalid integer value.")
                    input("\nPress Enter to continue...")
                    return
            elif key in ["temperature", "top_p"]:
                try:
                    new_value = float(new_value)
                except ValueError:
                    print("Invalid float value.")
                    input("\nPress Enter to continue...")
                    return
            
            setattr(config, key, new_value)
            
            # Save normalized path to config file for folder paths, or the raw value for other settings
            try:
                with open(config_file_path, 'r') as f:
                    config_data = json.load(f)
            except FileNotFoundError:
                config_data = {}
            
            # For folder paths, save the normalized absolute path
            if key in ["output_folder", "input_resumes_folder", "job_descriptions_folder"]:
                config_data[key] = os.path.abspath(new_value)
            else:
                config_data[key] = new_value
            
            with open(config_file_path, 'w') as f:
                json.dump(config_data, f, indent=4)
            
            print(f"Setting '{name}' updated successfully.")
        else:
            print("No changes made.")
    else:
        print("Invalid setting choice.")
    
    input("\nPress Enter to continue...")

def view_available_files(config):
    """View available input resumes and job descriptions"""
    while True:
        print("\n--- Available Files ---")
        print("1. View input resumes")
        print("2. View job descriptions")
        print("3. Back to main menu")
        
        choice = input("Enter your choice (1-3): ").strip()
        
        if choice == "1":
            view_input_resumes(config)
        elif choice == "2":
            view_job_descriptions(config)
        elif choice == "3":
            break
        else:
            print("Invalid choice. Please try again.")

def view_input_resumes(config):
    """Display available input resumes"""
    print(f"\n--- Input Resumes (in {config.input_resumes_folder}) ---")
    if not os.path.exists(config.input_resumes_folder):
        print(f"Folder '{config.input_resumes_folder}' does not exist.")
    else:
        resume_files = [f for f in os.listdir(config.input_resumes_folder) if f.endswith(('.txt', '.md', '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'))]
        if not resume_files:
            print("No resume files found.")
        else:
            for i, resume in enumerate(resume_files, 1):
                print(f"{i}. {resume}")
    input("\nPress Enter to continue...")

def view_job_descriptions(config):
    """Display available job descriptions"""
    print(f"\n--- Job Descriptions (in {config.job_descriptions_folder}) ---")
    if not os.path.exists(config.job_descriptions_folder):
        print(f"Folder '{config.job_descriptions_folder}' does not exist.")
    else:
        try:
            state_manager = StateManager()
            input_handler = InputHandler(state_manager, job_description_folder=config.job_descriptions_folder)
            job_descriptions = input_handler.get_job_descriptions()
            if not job_descriptions:
                print("No job descriptions found.")
            else:
                for i, jd in enumerate(job_descriptions.keys(), 1):
                    print(f"{i}. {jd}")
        except Exception as e:
            print(f"Error reading job descriptions: {e}")
    input("\nPress Enter to continue...")

def test_ocr_functionality(config):
    """Test OCR functionality on image files"""
    print("\n--- OCR Functionality Test ---")
    
    # Check if Tesseract is available
    try:
        import pytesseract
        from input_handler import InputHandler
        from state_manager import StateManager
        
        # Try to get Tesseract version to verify it's installed
        pytesseract.get_tesseract_version()
        print("Tesseract OCR is available.")
    except Exception as e:
        print(f"OCR functionality is not available: {e}")
        print("Please ensure Tesseract OCR is installed and added to your system PATH.")
        input("\nPress Enter to continue...")
        return
    
    # Get available image files
    if not os.path.exists(config.input_resumes_folder):
        print(f"Input folder '{config.input_resumes_folder}' does not exist.")
        input("\nPress Enter to continue...")
        return
    
    image_files = [f for f in os.listdir(config.input_resumes_folder)
                   if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'))]
    
    if not image_files:
        print("No image files found in the input folder.")
        input("\nPress Enter to continue...")
        return
    
    print("Available image files:")
    for i, image_file in enumerate(image_files, 1):
        print(f"{i}. {image_file}")
    
    choice = input("\nEnter the number of the image file to test OCR on (or 0 to go back): ").strip()
    if choice == "0":
        return
    elif choice.isdigit() and 1 <= int(choice) <= len(image_files):
        selected_file = image_files[int(choice) - 1]
        file_path = os.path.join(config.input_resumes_folder, selected_file)
        
        try:
            # Use InputHandler to extract text from image
            state_manager = StateManager()
            input_handler = InputHandler(state_manager)
            extracted_text = input_handler.extract_text_from_image(file_path)
            
            if extracted_text.strip():
                print(f"\n--- OCR Results for {selected_file} ---")
                print(extracted_text)
                print("\n--- End of OCR Results ---")
            else:
                print(f"Could not extract text from {selected_file}. The image may be empty or unreadable.")
        except Exception as e:
            print(f"Error processing image file: {e}")
    else:
        print("Invalid choice.")
    
    input("\nPress Enter to continue...")

def view_generated_outputs(config):
    """View generated output files"""
    print(f"\n--- Generated Outputs (in {config.output_folder}) ---")
    if not os.path.exists(config.output_folder):
        print(f"Folder '{config.output_folder}' does not exist.")
        input("\nPress Enter to continue...")
        return
    
    output_files = [f for f in os.listdir(config.output_folder) if f.endswith('.txt')]
    if not output_files:
        print("No output files found.")
        input("\nPress Enter to continue...")
        return
    
    print("Available output files:")
    for i, output_file in enumerate(output_files, 1):
        print(f"{i}. {output_file}")
    
    choice = input("\nEnter the number of the file to view (or 0 to go back): ").strip()
    if choice == "0":
        return
    elif choice.isdigit() and 1 <= int(choice) <= len(output_files):
        selected_file = output_files[int(choice) - 1]
        file_path = os.path.join(config.output_folder, selected_file)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"\n--- Content of {selected_file} ---")
            print(content)
            print("\n--- End of file ---")
        except Exception as e:
            print(f"Error reading file: {e}")
    else:
        print("Invalid choice.")
    
    input("\nPress Enter to continue...")

def main_menu(config, config_file_path):
    """Main menu loop"""
    while True:
        display_menu()
        choice = input("Enter your choice (1-6): ").strip()
        
        if choice == "1":
            process_resumes_menu(config)
        elif choice == "2":
            view_edit_settings(config, config_file_path)
        elif choice == "3":
            view_available_files(config)
        elif choice == "4":
            view_generated_outputs(config)
        elif choice == "5":
            test_ocr_functionality(config)
        elif choice == "6":
            print("Thank you for using ATS Resume Checker!")
            break
        else:
            print("Invalid choice. Please try again.")

def main():
    parser = argparse.ArgumentParser(description="ATS Checker")
    parser.add_argument("--config_file", type=str, default="config.json",
                        help="Path to the configuration JSON file.")
    parser.add_argument("--job_description", type=str,
                        help="Optional: Name of the job description file (e.g., 'software_engineer.txt') to tailor resumes.")
    args = parser.parse_args()
    config = load_config(config_file_path=args.config_file, cli_args=args)

    # Create output folder if it doesn't exist
    os.makedirs(config.output_folder, exist_ok=True)

    # Check if we're running with CLI arguments for backward compatibility
    if args.job_description:
        # Run in CLI mode for backward compatibility
        try:
            state_manager = StateManager() # Initialize StateManager here
            input_handler = InputHandler(state_manager, job_description_folder=config.job_descriptions_folder)

            job_description_to_use = None
            if args.job_description:
                job_descriptions = input_handler.get_job_descriptions()
                if args.job_description in job_descriptions:
                    job_description_to_use = args.job_description
                    logging.info(f"Selected job description: {job_description_to_use}")
                else:
                    logging.warning(f"Job description '{args.job_description}' not found in '{config.job_descriptions_folder}'. Processing without tailoring.")
            else:
                logging.info("No specific job description provided. Processing all resumes without tailoring.")

            logging.info(f"Starting resume processing for input folder: {config.input_resumes_folder}")
            processor = ResumeProcessor(
                input_folder=config.input_resumes_folder,
                output_folder=config.output_folder,
                model_name=config.model_name,
                temperature=config.temperature,
                top_p=config.top_p,
                top_k=config.top_k,
                max_output_tokens=config.max_output_tokens,
                num_versions_per_job=config.num_versions_per_job,
                job_description_folder=config.job_descriptions_folder # Pass job_description_folder
            )
            processor.process_resumes(job_description_name=job_description_to_use)
            logging.info("Resume processing completed successfully.")
        except ValueError as e:
            logging.error(f"Configuration Error: {e}")
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}", exc_info=True)
    else:
        # Run in interactive menu mode
        main_menu(config, args.config_file)

if __name__ == "__main__":
    main()