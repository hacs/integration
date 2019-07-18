# Theming

HACS will try to match your Home Assistant theme as much as possible. There are also two variables
specific to the HACS badge text and background colors (for new items in the store and to categorize custom repositories on the settings):

They are `--hacs-badge-color` and `--hacs-badge-text-color`. You can customize them in your `themes.yaml` file by setting them to another
theming variable or their own color. For example:

`hacs-badge-text-color: "var(--text-primary-color)"`

<!-- Disable sidebar -->
<script>
let sidebar = document.getElementsByClassName("col-md-3")[0];
sidebar.parentNode.removeChild(sidebar);
document.getElementsByClassName("col-md-9")[0].style['padding-left'] = "0";
</script>
<!-- Disable sidebar -->
