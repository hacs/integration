# Theming

HACS will try to match your Home Assistant theme as much as possible. There are also several variables you can use in your `themes.yaml` file to theme HACS further:

| Variable  | Usage |
| ------------- | ------------- |
| `hacs-badge-color`  | Controls the background color on the "NEW" badges in the store, and the custom repository type badges in settings  |
| `hacs-badge-text-color`  | Controls the text color on the "NEW" badges in the store, and the custom repository type badges in settings  |
| `hacs-status-installed`  | Controls the icon color for installed, up-to-date components  |
| `hacs-status-pending-restart`  | Controls the icon color for installed components that are awaiting a Home Assistant restart  |
| `hacs-status-pending-update`  | Controls the icon color for installed components that have an update available  |

Here's a basic example of customizing one of these variables in `themes.yaml`:

`hacs-badge-text-color: "var(--text-primary-color)"`

<!-- Disable sidebar -->
<script>
let sidebar = document.getElementsByClassName("col-md-3")[0];
sidebar.parentNode.removeChild(sidebar);
document.getElementsByClassName("col-md-9")[0].style['padding-left'] = "0";
</script>
<!-- Disable sidebar -->
