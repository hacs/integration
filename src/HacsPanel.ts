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

import "./panels/installed";
import "./panels/integrations";
import "./panels/settings";

@customElement("hacs-panel")
export class HacsPanel extends LitElement {
  @property() public hass!: HomeAssistant;

  @property() public repositories;

  @property() public panel!: String;

  updated(changedProperties: any) {
    console.log('updated');
    changedProperties.forEach((oldValue: any, propName: any, newValue: any) => {
      console.log(`${propName} changed. oldValue: ${oldValue}, newValue: ${newValue}`);
    });
  }

  protected render(): TemplateResult | void {
    console.log('hass: ' + this.hass)
    console.log('repositories: ' + this.repositories)
    console.log('panel: ' + this.panel)
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