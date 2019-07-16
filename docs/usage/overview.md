# Overview

_During startup HACS loads all known repositories. When it does you will see a progress bar at the top of the page, if will not go away on it's own, try refreshing the browser window after a couple of minutes._

The overview tab in HACS contains all the repositories HACS manages that you have installed.

![overview](../images/overview.png)

To change the layout have a look at the [HACS Display option](../settings/#hacs-option-display).

The repositories are sorted by type.

If you click anywhere on the card you will get to the [Repository view](./repository.md) of that repository.

## Card elements

Every repository is represented as a card. Each card displays the title and description of the repository and an icon indicating the current status.

### Repository status

The status icon gives you a quick indication of the status of the repository.

color | description
-- | --
Green | The repository is installed and there is no pending actions.
Orange | There is an update available.
Red | There is an restart pending.
No color (the default text color of the theme) | Repository is not installed/managed by HACS.

<!-- Disable sidebar -->
<script>
let sidebar = document.getElementsByClassName("col-md-3")[0];
sidebar.parentNode.removeChild(sidebar);
document.getElementsByClassName("col-md-9")[0].style['padding-left'] = "0";
</script>
<!-- Disable sidebar -->
