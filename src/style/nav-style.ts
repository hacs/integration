import { css } from "lit-element";

export const navStyle = css`
    :host {
      font-family: var(--paper-font-body1_-_font-family); -webkit-font-smoothing: var(--paper-font-body1_-_-webkit-font-smoothing); font-size: var(--paper-font-body1_-_font-size); font-weight: var(--paper-font-body1_-_font-weight); line-height: var(--paper-font-body1_-_line-height);
    }

    app-header-layout, ha-app-layout {
      background-color: var(--primary-background-color);
    }

    app-header, app-toolbar, paper-tabs {
      background-color: var(--primary-color);
      font-weight: 400;
      text-transform: uppercase;
      color: var(--text-primary-color, white);
    }

    paper-tabs {
      --paper-tabs-selection-bar-color: #fff;
      margin-left: 12px;
    }

    app-toolbar ha-menu-button + [main-title], app-toolbar ha-paper-icon-button-arrow-prev + [main-title], app-toolbar paper-icon-button + [main-title] {
      margin-left: 24px;
    }
`