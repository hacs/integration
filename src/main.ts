import {
  LitElement,
  html,
  customElement,
  CSSResult,
  TemplateResult,
  css
} from "lit-element";

import { HacsCard } from "./HacsCard"
import { HomeAssistantObject } from "./HomeAssistantObject"


customElements.define('hacs-overview-card', HacsCard);
// TODO Name your custom element
@customElement("boilerplate-card")
class BoilerplateCard extends LitElement {
  public hass = (parent.document.querySelector('home-assistant') as HomeAssistantObject).hass;

  protected render(): TemplateResult | void {

    // TODO Check for stateObj or other necessary things and render a warning if missing
    return html`
          <hacs-overview-card
          header="${this.hass.localize("component.hacs.config.title")}"
          >content</hacs-overview-card>
        `;
  }

  static get styles(): CSSResult {
    return css`
          .warning {
            display: block;
            color: black;
            background-color: #fce588;
            padding: 8px;
          }
        `;
  }
}