import arguably
import os
import glob
from pathlib import Path
import base64
import openai
import time
import subprocess
import tempfile
from dotenv import load_dotenv

load_dotenv()

@arguably.command
def hello(name: str = "World"):
    """
    A simple hello world command.
    
    Args:
        name: The name to greet (defaults to "World")
    """
    print(f"Helloooo, {name}!")

@arguably.command
def extract_book(
    directory: str,
    output_file: str = "to_read.md",
    image_extensions: str = "jpg,jpeg,png,heic",
):
    """
    Process book page images and extract their content into a markdown file.
    
    Args:
        directory: Relative path to directory containing book page images
        output_file: Name of output markdown file (default: to_read.md)
        image_extensions: Comma-separated list of image extensions to process (default: jpg,jpeg,png,heic)
    """

    client = openai.OpenAI()  # Will use OPENAI_API_KEY environment variable
    
    # Verify directory exists
    dir_path = Path(directory)
    if not dir_path.exists() or not dir_path.is_dir():
        print(f"Error: Directory '{directory}' does not exist or is not a directory")
        return
    
    # Find all images in the directory
    extensions = image_extensions.split(",")
    image_files = []
    for ext in extensions:
        # Add both lowercase and uppercase versions of the extension to catch all files
        ext = ext.strip()
        image_files.extend(glob.glob(f"{directory}/*.{ext.lower()}"))
        image_files.extend(glob.glob(f"{directory}/*.{ext.upper()}"))
    
    image_files.sort()  # Sort to maintain page order
    
    if not image_files:
        print(f"No images found in '{directory}' with extensions: {image_extensions}")
        return
    
    # image_files = image_files[:2]

    print(f"Found {len(image_files)} images to process")
    
    # Process each image
    full_content = []
    for i, img_path in enumerate(image_files):
        print(f"Processing image {i+1}/{len(image_files)}: {img_path}")
        
        # Handle HEIC images by converting them to JPEG using sips (macOS) or magick (ImageMagick)
        if img_path.lower().endswith('.heic'):
            try:
                # Create a temporary file for the converted image
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                    temp_jpg_path = temp_file.name
                
                # Try sips (macOS) first
                try:
                    subprocess.run(['sips', '-s', 'format', 'jpeg', img_path, '--out', temp_jpg_path], 
                                  check=True, capture_output=True)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    # If sips fails, try ImageMagick
                    try:
                        subprocess.run(['magick', img_path, temp_jpg_path], 
                                      check=True, capture_output=True)
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        print(f"Error: Could not convert HEIC image {img_path}. "
                              f"Please install sips (macOS) or ImageMagick.")
                        continue
                
                # Read the converted image
                with open(temp_jpg_path, "rb") as img_file:
                    base64_image = base64.b64encode(img_file.read()).decode("utf-8")
                
                # Clean up the temporary file
                os.unlink(temp_jpg_path)
                
            except Exception as e:
                print(f"Error converting HEIC image {img_path}: {str(e)}")
                continue
        else:
            # Encode other image formats to base64
            with open(img_path, "rb") as img_file:
                base64_image = base64.b64encode(img_file.read()).decode("utf-8")
        
        try:
            # Call OpenAI API to process the image
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text", 
                                "text": "Extract all text content from this book page. Format it properly as markdown. Don't include the markdown wrapper in the response, just return the formattedmarkdown content."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4096,
                temperature=0.0
            )
            
            # Extract the text content from the response
            page_content = response.choices[0].message.content
            full_content.append(f"{page_content}\n\n---\n---\n\n")
            
            # Sleep briefly to avoid rate limits
            time.sleep(1)
            
        except Exception as e:
            print(f"Error processing image {img_path}: {str(e)}")
    
    # Write the content to the output file
    output_path = Path(directory, '..', output_file)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("".join(full_content))
    
    print(f"Successfully extracted content from {len(image_files)} pages")
    print(f"Output written to: {output_path.absolute()}")

if __name__ == "__main__":
    arguably.run() 
