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

  @property()
  public panel!: string;

  protected render(): TemplateResult | void {
    return html`

    <p>${this.hass}</p></br>
    <p>${this.repositories}</p></br>
    <p>${this.panel}</p></br>
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