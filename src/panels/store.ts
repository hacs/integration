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

import { Configuration, Repositories } from "../types"

@customElement("hacs-panel-store")
export class HacsPanelStore extends LitElement {

  @property()
  public hass!: HomeAssistant;

  @property()
  public repositories!: Repositories

  @property()
  public configuration!: Configuration

  @property()
  public panel;

  protected render(): TemplateResult | void {
    const category = this.panel;
    const config = this.configuration
    var _repositories = this.repositories.content || [];
    _repositories = this.repositories.content.filter(function (repo) {

      if (category === "store") {
        // Hide HACS from the store
        if (repo.id === "172733314") return false;

        // Hide hidden repos from the store
        if (repo.hide) return false;

        // Check contry restrictions
        if (config.country !== null) {
          if (config.country !== repo.country) return false;
        }

      }

      // Object looks OK, let's show it
      if (repo.category === category) return true;

      // Fallback to not showing it.
      return false
    });

    return html`
    <div class="hacs-repositories">
    ${_repositories.sort((a, b) => (a.name > b.name) ? 1 : -1).map(repo =>
      html`<ha-card header="${repo.name}">
      <div class="card-content">
        <i>${repo.description}<i>
      </div>
      </ha-card>
      `)}
    </div>
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