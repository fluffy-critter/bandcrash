import sphinx_rtd_theme
project = "bandcrash"
master_doc = "index"
extensions = ["sphinx.ext.autodoc"]
autoclass_content = "both"
autodoc_member_order = "groupwise"
autodoc_inherit_docstrings = False
html_logo = "../art/bclogo.svg"

html_theme = 'sphinx_rtd_theme'
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
