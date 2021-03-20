import setuptools
import podcast_encoder

with open("README.md", "r") as f:
    long_description = f.read()

setuptools.setup(
    name="podcast-encoder",
    version=podcast_encoder.__version__,
    author="Sam Hutchins",
    description="Turn WAV files with CUE markers into MP3s with chapters",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/samhutchins/podcast-encoder",
    packages=["podcast_encoder"],
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
    entry_points={
        "console_scripts": [
            'encode-podcast=podcast_encoder.encode_podcast:main'
        ]
    }
)