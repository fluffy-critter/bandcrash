project = "bandcrash"
master_doc = "index"
extensions = ["sphinx.ext.autodoc", "sphinx_copybutton"]
autoclass_content = "both"
autodoc_member_order = "groupwise"
autodoc_inherit_docstrings = False
html_logo = "../art/bclogo.svg"

# These folders are copied to the documentation's HTML output
html_static_path = ['_static']

# These paths are either relative to html_static_path
# or fully qualified paths (eg. https://...)
html_css_files = [
    'css/custom.css',
]
