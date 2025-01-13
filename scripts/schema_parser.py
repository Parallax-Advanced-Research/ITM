import os
import requests
import shutil
import subprocess

# Constants
SCHEMA_URL = "https://raw.githubusercontent.com/NextCenturyCorporation/itm-evaluation-server/development/swagger/swagger.yaml"
SCHEMA_FILE = "current_schema.yaml"
OUTPUT_DIR = "./domain/enum/ta3_schema"
TMP_DIR = "./tmp"

def download_schema():
    """Download the schema file from the specified URL."""
    print(f"Downloading schema from {SCHEMA_URL}...")
    response = requests.get(SCHEMA_URL)
    if response.status_code == 200:
        with open(SCHEMA_FILE, "w") as f:
            f.write(response.text)
        print(f"Schema downloaded: {SCHEMA_FILE}")
    else:
        raise Exception(f"Failed to download schema. Status code: {response.status_code}")

def run_openapi_generator():
    """Run OpenAPI generator to create Python client and models."""
    print("Running OpenAPI generator...")
    try:
        command = [
            "openapi-generator-cli", "generate",
            "-i", SCHEMA_FILE,
            "-g", "python",
            "-o", TMP_DIR
        ]

        result = subprocess.run(command, check=True, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Failed to run OpenAPI generator: {e}")
        print(f"Error output:\n{e.stderr}")
        raise

def post_process_models():
    """Extract and process Pydantic models from generated output."""
    models_dir = os.path.join(TMP_DIR, "openapi_client", "models")
    if not os.path.exists(models_dir):
        raise Exception(f"Models directory not found: {models_dir}")

    print("Post-processing models...")
    # Remove imports for `openapi_client.models`
    for root, _, files in os.walk(models_dir):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                with open(file_path, "r") as f:
                    content = f.read()
                content = content.replace("openapi_client.models", "")
                with open(file_path, "w") as f:
                    f.write(content)

    # Clear old models and move the new ones
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    shutil.move(models_dir, OUTPUT_DIR)
    print(f"Models moved to {OUTPUT_DIR}")

def cleanup():
    """Remove temporary files and the schema file."""
    if os.path.exists(TMP_DIR):
        shutil.rmtree(TMP_DIR)
    if os.path.exists(SCHEMA_FILE):
        os.remove(SCHEMA_FILE)
    print("Cleaned up temporary files.")

def main():
    """Main script execution."""
    try:
        print("Starting the schema processing...")
        download_schema()       # Step 1: Download the schema
        run_openapi_generator() # Step 2: Run OpenAPI generator
        post_process_models()   # Step 3: Process and move models
        print("Schema processing completed successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup()               # Step 4: Cleanup temporary files

if __name__ == "__main__":
    main()
