from setuptools import setup, find_packages

setup(
    name="ai-media-tools",
    version="0.1.0",
    description="A suite of tools to greatly simplify the youtube content creation process",
    long_description="There are functions that will create your thumbnails, video scripts, transcribe other videos and translate them, trim and zoom, split and recombine for compilations, etc. most functions run on multiple threads and those that encode the videos use whatever GPU you have",
    author="Saad Aaqiq",
    author_email="saad.aaqiq@polytechnique.edu",
    url="https://github.com/yourusername/your-package-name",
    packages=find_packages(),
    install_requires=[
        # List your dependencies here
        "openai",
        "httplib2",
        "keyboard",
        "requests",
        "beautifulsoup4",
        "Pillow",
        "rembg",
        "pillar-youtube-upload",
        "glob2",
        "python-Levenshtein",
        "gradio-client",
        "joblib",
        "threading",
        "ahk",
        "num2words",
        "roman"
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
    ],
)
