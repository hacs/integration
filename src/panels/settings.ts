import {
  LitElement,
  customElement,
  CSSResult,
  TemplateResult,
  html,
  css,
  property
} from "lit-element";

import {
  HomeAssistant
} from "custom-card-helpers";


@customElement("hacs-panel-settings")
export class HacsPanelSettings extends LitElement {
  @property()
  public hass!: HomeAssistant;

  @property()
  public repositories;

  render(): TemplateResult | void {
    console.log('hass: ', this.hass)
    return html`

    <ha-card header="${this.hass.localize("component.hacs.config.title")}">

    </ha-card>
          `;
  }

  static get styles(): CSSResult {
    return css`
      :host {
        color: var(--primary-text-color);
      }
      ha-card {
        margin: 8px;
      }
      `;
  }
}