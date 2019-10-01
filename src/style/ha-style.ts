import { css } from "lit-element";

export const haStyle = css`
    :host {
      @apply --paper-font-body1;
    }

    app-header-layout,
    ha-app-layout {
      background-color: var(--primary-background-color);
    }

    app-header, app-toolbar {
      background-color: var(--primary-color);
      font-weight: 400;
      color: var(--text-primary-color, white);
    }

    app-toolbar ha-menu-button + [main-title],
    app-toolbar ha-paper-icon-button-arrow-prev + [main-title],
    app-toolbar paper-icon-button + [main-title] {
      margin-left: 24px;
    }

    button.link {
      background: none;
      color: inherit;
      border: none;
      padding: 0;
      font: inherit;
      text-align: left;
      text-decoration: underline;
      cursor: pointer;
    }

    .card-actions a {
      text-decoration: none;
    }

    .card-actions .warning {
      --mdc-theme-primary: var(--google-red-500);
    }
`;