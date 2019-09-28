import {
  LitElement,
  customElement,
  CSSResultArray,
  TemplateResult,
  html,
  property
} from "lit-element";

import { HomeAssistant } from "custom-card-helpers";
import { HacsStyle } from "../style/hacs-style"

import { Configuration, Repositories } from "../types"

@customElement("hacs-panel-settings")
export class HacsPanelSettings extends LitElement {
  @property()
  public hass!: HomeAssistant;

  @property()
  public repositories!: Repositories

  @property()
  public configuration!: Configuration

  render(): TemplateResult | void {
    console.log('hass: ', this.hass)
    console.log('configuration: ', this.configuration)
    return html`

    <ha-card header="${this.hass.localize("component.hacs.config.title")}">
      <div class="card content">



      </div>
    </ha-card>
          `;
  }

  static get styles(): CSSResultArray {
    return [HacsStyle]
  }
}