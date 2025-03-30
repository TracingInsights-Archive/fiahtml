import os

def create_nojekyll(output_dir):
    """Create a .nojekyll file in the output directory to disable Jekyll processing"""
    nojekyll_path = os.path.join(output_dir, ".nojekyll")
    with open(nojekyll_path, "w") as f:
        pass  # Create an empty file
    print(f"Created .nojekyll file at {nojekyll_path}")

if __name__ == "__main__":
    # Default output directory is 'docs' for GitHub Pages
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")

    # Create the output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    create_nojekyll(output_dir)