import {
  LitElement,
  TemplateResult,
  html,
  CSSResultArray,
  css,
  customElement,
  property,
} from "lit-element";

import { HomeAssistantObject } from './HomeAssistantObject'

@customElement("hacs-header")
export class HAPanelDeveloperTools extends LitElement {
  public hass = (parent.document.querySelector('home-assistant') as HomeAssistantObject).hass;
  @property() public narrow!: boolean;

  protected render(): TemplateResult | void {
    const page = null; //this._page;
    return html`
      <app-header-layout has-scrolling-region>
        <app-header fixed slot="header">
          <app-toolbar>
            <ha-menu-button
              .hass=${this.hass}
              .narrow=${this.narrow}
            ></ha-menu-button>
            <div main-title>${this.hass.localize("component.hacs.config.title")}</div>
          </app-toolbar>

          <paper-tabs
            scrollable
            attr-for-selected="page-name"
            .selected=${page}
          >
            <paper-tab page-name="state">
            ${this.hass.localize("component.hacs.common.overview")}
            </paper-tab>
            <paper-tab page-name="service">
            ${this.hass.localize("component.hacs.common.store")}
            </paper-tab>
            <paper-tab page-name="logs">
            ${this.hass.localize("component.hacs.common.settings")}
            </paper-tab>
          </paper-tabs>
        </app-header>
      </app-header-layout>
    `;
  }

  static haStyle = css`
  :host {
    @apply --paper-font-body1;
  }
  app-header-layout,
  ha-app-layout {
    background-color: var(--primary-background-color);
  }
  app-header,
  app-toolbar {
    background-color: var(--primary-color);
    font-weight: 400;
    color: var(--text-primary-color, white);
  }
  app-toolbar ha-menu-button + [main-title],
  app-toolbar ha-paper-icon-button-arrow-prev + [main-title],
  app-toolbar paper-icon-button + [main-title] {
    margin-left: 24px;
  }
  h1 {
    @apply --paper-font-title;
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

  static get styles(): CSSResultArray {
    return [
      HAPanelDeveloperTools.haStyle,
      css`
        :host {
          color: var(--primary-text-color);
          --paper-card-header-color: var(--primary-text-color);
        }
        paper-tabs {
          margin-left: 12px;
          --paper-tabs-selection-bar-color: #fff;
          text-transform: uppercase;
        }
      `,
    ];
  }
}