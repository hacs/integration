import {
  LitElement,
  customElement,
  CSSResultArray,
  TemplateResult,
  html,
  css,
  property
} from "lit-element";
import { unsafeHTML } from 'lit-html/directives/unsafe-html';
import { HomeAssistant } from "custom-card-helpers";
import { HacsStyle } from "../style/hacs-style"

import { Configuration, Repository } from "../types"
import { navigate } from "../misc/navigate"
import "../misc/HacsSpinner"
import "./corePanel"

@customElement("hacs-panel-repository")
export class HacsPanelRepository extends LitElement {
  @property()
  public hass!: HomeAssistant;

  @property()
  public repositories!: Repository[];

  @property()
  public configuration!: Configuration;

  @property()
  public repository!: string;

  @property()
  public panel;

  @property()
  public repository_view = false;

  repo: Repository;

  private UpdateRepositoryData(): void {
    this.hass.connection.sendMessagePromise({
      type: "hacs/repository",
      action: "update",
      repository: this.repository
    }).then(
      (resp) => {
        this.repositories = (resp as Repository[]);
      },
      (err) => {
        console.error('Message failed!', err);
      }
    )
    this.requestUpdate();

  };

  protected firstUpdated() {
    this.UpdateRepositoryData()
  }


  render(): TemplateResult | void {
    if (this.repository === undefined) {
      return html`
      <hacs-panel
      .hass=${this.hass}
      .configuration=${this.configuration}
      .repositories=${this.repositories}
      .panel=${this.panel}
      .repository_view=${this.repository_view}
      .repository=${this.repository}
      >
      </hacs-panel>
      `
    }
    var _repository = this.repository;
    var _repositories = this.repositories || [];
    _repositories = this.repositories.filter(function (repo) {
      return repo.id === _repository
    });
    this.repo = _repositories[0]

    if (!this.repo.updated_info) return html`<hacs-spinner></hacs-spinner>`;

    if (this.repo.installed) {
      var back = `
        ${this.hass.localize(`component.hacs.repository.back_to`)} ${this.hass.localize(`component.hacs.repository.installed`)}
        `;
    } else {
      if (this.repo.category === "appdaemon") {
        var FE_cat = "appdaemon_apps";
      } else {
        FE_cat = `${this.repo.category}s`
      }
      var back = `
        ${this.hass.localize(`component.hacs.repository.back_to`)} ${this.hass.localize(`component.hacs.common.${FE_cat}`)}
        `;
    }

    return html`

    <div class="getBack">
      <mwc-button @click=${this.GoBackToStore} title="${back}">
      <ha-icon  icon="mdi:arrow-left"></ha-icon>
        ${back}
      </mwc-button>
    </div>

    <ha-card header="${this.repo.name}">
      <div class="card-content addition">
        <div class="description">
          ${this.repo.description}
        </div>
      </div>
      <div class="card-actions">
      </div>
    </ha-card>

    <ha-card>
      <div class="card-content">
        <div class="more_info">
          ${unsafeHTML(this.repo.additional_info)}
        </div>
      </div>
    </ha-card>
          `;
  }

  GoBackToStore() {

    this.repository = undefined;
    if (this.repo.installed) {
      this.panel = "installed"
    } else {
      this.panel = this.repo.category
    }
    navigate(this, `/hacs/${this.repo.category}`)
    this.requestUpdate();
  }

  static get styles(): CSSResultArray {
    return [HacsStyle, css`
      .description {
        font-style: italic;
      }
      .getBack {
        margin-top: 8px;
        margin-bottom: 4px;
        margin-left: 5%;
      }
      ha-card {
        width: 90%;
        margin-left: 5%;
      }
    `]
  }
}