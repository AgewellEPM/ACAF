# setup.py
# Defines how the project can be packaged and installed.

from setuptools import setup, find_packages

setup(
    name='worker-mind-ai',
    version='0.1.0',
    packages=find_packages(where='src'), # Look for packages in the 'src' directory
    package_dir={'': 'src'},             # Tell setuptools that packages are under 'src'
    include_package_data=True,           # Include non-code files specified in MANIFEST.in
    install_requires=[
        'openai>=1.0.0',  # For LLM interactions
        'python-dotenv>=1.0.0', # For loading environment variables
        'tk', # Tkinter is usually part of Python, but good to note for dependencies
        # Add any other third-party libraries your project uses
    ],
    entry_points={
        'console_scripts': [
            'worker-mind-gui=gui.WorkerMindDashboard:main', # Entry point for the GUI
        ],
    },
    author='Your Name',
    author_email='your.email@example.com',
    description='An autonomous AI agent framework with reflection, planning, and tool use.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/WorkerMind-AI', # Replace with your GitHub URL
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License', # Or your chosen license
        'Operating System :: OS Independent',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
    ],
    python_requires='>=3.9', # Specify minimum Python version
    keywords='ai autonomous agent llm reflection planning tools',
)
