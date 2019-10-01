import { CSSResultArray, css } from "lit-element";

import { haStyle } from "./ha-style"
import { navStyle } from "./nav-style"

const customHacsStyles = css`
    :host {
        --hacs-status-installed: #126e15;
        --hacs-status-pending-restart: #a70000;
        --hacs-status-pending-update: #ffab40;
        --hacs-status-default: var(--primary-text-color);
        --hacs-badge-color: var(--primary-color);
        --hacs-badge-text-color: var(--primary-text-color);
      }
`

const baseHacsStyles = css`
    :root {
        font-family: var(--paper-font-body1_-_font-family);
        -webkit-font-smoothing: var(--paper-font-body1_-_-webkit-font-smoothing);
        font-size: var(--paper-font-body1_-_font-size);
        font-weight: var(--paper-font-body1_-_font-weight);
        line-height: var(--paper-font-body1_-_line-height);
    }
    a {
        text-decoration: none;
        color: var(--dark-primary-color);
    }
    h1 {
        font-family: var(--paper-font-title_-_font-family);
        -webkit-font-smoothing: var(--paper-font-title_-_-webkit-font-smoothing);
        white-space: var(--paper-font-title_-_white-space);
        overflow: var(--paper-font-title_-_overflow);
        text-overflow: var(--paper-font-title_-_text-overflow);
        font-size: var(--paper-font-title_-_font-size);
        font-weight: var(--paper-font-title_-_font-weight);
        line-height: var(--paper-font-title_-_line-height);
        @apply --paper-font-title;
    }
    .title {
        margin-bottom: 16px;
        padding-top: 4px;
        color: var(--primary-text-color);
        white-space: nowrap;
        text-overflow: ellipsis;
        overflow: hidden;
    }
    .addition {
        color: var(--secondary-text-color);
        position: relative;
        height: auto;
        line-height: 1.2em;
        text-overflow: ellipsis;
        overflow: hidden;
    }
    paper-card {
        cursor: pointer;
    }
    ha-card {
      margin: 8px;
    }
    ha-icon {
        margin-right: 16px;
        float: left;
        color: var(--primary-text-color);
    }
      ha-icon.installed {
        color: var(--hacs-status-installed);
    }
      ha-icon.pending-upgrade {
        color: var(--hacs-status-pending-update);
    }
      ha-icon.pending-restart {
        color: var(--hacs-status-pending-restart);
    }
`



export const HacsStyle: CSSResultArray = [haStyle, navStyle, baseHacsStyles, customHacsStyles]
