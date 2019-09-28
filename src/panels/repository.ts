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
import { navigate } from "../navigate"
import "./store"

@customElement("hacs-panel-repository")
export class HacsPanelRepository extends LitElement {
  @property()
  public hass!: HomeAssistant;

  @property()
  public repositories!: Repositories;

  @property()
  public configuration!: Configuration;

  @property()
  public repository!: string;

  @property()
  public panel;

  @property()
  public repository_view = false;

  render(): TemplateResult | void {
    if (this.repository === undefined) {
      return html`
      <hacs-panel-store
      .hass=${this.hass}
      .configuration=${this.configuration}
      .repositories=${this.repositories}
      .panel=${this.panel}
      .repository_view=${this.repository_view}
      .repository=${this.repository}
      >
      </hacs-panel-store>
      `
    }
    var _repository = this.repository;
    var _repositories = this.repositories.content || [];
    _repositories = this.repositories.content.filter(function (repo) {
      return repo.id === _repository
    });
    var repo = _repositories[0]
    return html`

    <mwc-button @click=${this.GoBackToStore} title="Back to Integrations store">
    <ha-icon  icon="mdi:arrow-left"></ha-icon>
      Back to Integrations store
    </mwc-button>

    <ha-card header="${repo.name}">
      <div class="card content">
      </div>
    </ha-card>
          `;
  }

  GoBackToStore() {
    this.repository = undefined;
    this.panel = "integration"
    navigate(this, "/hacs/integration")
    this.requestUpdate();
  }

  static get styles(): CSSResult {
    return css`
      :host {
        color: var(--primary-text-color);
      }
      ha-card {
        margin: 8px;
        width: 90%;
        margin-left: 5%;
      }
      `;
  }
}