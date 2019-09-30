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
import "../misc/RepositoryNote"
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



  private RepositoryWebSocketAction(Action: string): void {
    this.hass.connection.sendMessagePromise({
      type: "hacs/repository",
      action: Action,
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
    if (!this.repo.updated_info) this.RepositoryWebSocketAction("update");
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
    var _repositories = this.repositories.filter(function (repo) {
      return repo.id === _repository
    });
    this.repo = _repositories[0]

    if (!this.repo.updated_info) return html`
    <hacs-spinner></hacs-spinner>
    <div class="loading">
      ${this.hass.localize(`component.hacs.repository.loading`)}
    </div>
    `;

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
      <paper-menu-button no-animations horizontal-align="right" role="group" aria-haspopup="true" vertical-align="top" aria-disabled="false">
        <paper-icon-button icon="hass:dots-vertical" slot="dropdown-trigger" role="button"></paper-icon-button>
        <paper-listbox slot="dropdown-content" role="listbox" tabindex="0">

        <paper-item @click=${this.RepositoryReload}>
        ${this.hass.localize(`component.hacs.repository.update_information`)}
        </paper-item>

      ${(this.repo.version_or_commit === "version" ? html`
      <paper-item @click=${this.RepositoryBeta}>
      ${(this.repo.beta ?
          this.hass.localize(`component.hacs.repository.hide_beta`) :
          this.hass.localize(`component.hacs.repository.show_beta`)
        )}
        </paper-item>`: "")}

        ${(!this.repo.custom ? html`
        <paper-item @click=${this.RepositoryHide}>
          ${this.hass.localize(`component.hacs.repository.hide`)}
        </paper-item>`: "")}

        <a href="https://google.com" rel='noreferrer' target="_blank">
          <paper-item>
            <ha-icon class="link-icon" icon="mdi:open-in-new"></ha-icon>
            ${this.hass.localize(`component.hacs.repository.open_issue`)}
          </paper-item>
        </a>

        <a href="https://google.com" rel='noreferrer' target="_blank">
          <paper-item>
            <ha-icon class="link-icon" icon="mdi:open-in-new"></ha-icon>
            ${this.hass.localize(`component.hacs.repository.flag_this`)}
          </paper-item>
        </a>

        </paper-listbox>
      </paper-menu-button>
      <div class="card-content">
        <div class="description addition">
          ${this.repo.description}
        </div>
        <div class="information">
          <div class="version installed">
            <b>${this.hass.localize(`component.hacs.repository.installed`)}: </b> ${this.repo.installed_version}
          </div>
          <div class="version available">
            <paper-dropdown-menu label="${this.hass.localize(`component.hacs.repository.available`)}">
              <paper-listbox slot="dropdown-content" selected="0">
                <paper-item>${this.repo.available_version}</paper-item>
                <paper-item>master</paper-item>
              </paper-listbox>
            </paper-dropdown-menu>
          </div>
        </div>
      </div>


      <div class="card-actions">

      <mwc-button @click=${this.RepositoryInstall}>
        ${this.hass.localize(`component.hacs.repository.${this.repo.main_action.toLowerCase()}`)}
      </mwc-button>

      ${(this.repo.pending_upgrade ? html`
      <a href="https://google.com" rel='noreferrer' target="_blank">
        <mwc-button>
        ${this.hass.localize(`component.hacs.repository.changelog`)}
        </mwc-button>
      </a>`: "")}

        <a href="https://google.com" rel='noreferrer' target="_blank">
          <mwc-button>
          ${this.hass.localize(`component.hacs.repository.repository`)}
          </mwc-button>
        </a>

      ${(this.repo.installed ? html`
        <mwc-button class="right" @click=${this.RepositoryUnInstall}>
          ${this.hass.localize(`component.hacs.repository.uninstall`)}
        </mwc-button>`: "")}


      </div>
    </ha-card>

    <ha-card>
      <div class="card-content">
        <div class="more_info">
          ${unsafeHTML(this.repo.additional_info)}
        </div>
      <hacs-repository-note
        .hass=${this.hass}
        .configuration=${this.configuration}
        .repository=${this.repo}
      ></hacs-repository-note>
      </div>
    </ha-card>
          `;
  }

  RepositoryReload() {
    this.RepositoryWebSocketAction("update");
  }

  RepositoryInstall() {
    this.RepositoryWebSocketAction("install");
  }

  RepositoryUnInstall() {
    this.RepositoryWebSocketAction("uninstall");
  }

  RepositoryBeta() {
    if (this.repo.beta) {
      this.RepositoryWebSocketAction("hide_beta");
    } else {
      this.RepositoryWebSocketAction("show_beta");
    }
  }

  RepositoryHide() {
    if (this.repo.hide) {
      this.RepositoryWebSocketAction("unhide");
    } else {
      this.RepositoryWebSocketAction("hide");
    }
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
        padding-bottom: 16px;
      }
      .version {
        padding-bottom: 8px;
      }
      .options {
        float: right;
        width: 40%;
      }
      .information {
        width: 60%;
      }
      .getBack {
        margin-top: 8px;
        margin-bottom: 4px;
        margin-left: 5%;
      }
      .right {
        float: right;
      }
      .loading {
        text-align: center;
        width: 100%;
      }
      ha-card {
        width: 90%;
        margin-left: 5%;
      }
      .link-icon {
        color: var(--dark-primary-color);
        margin-right: 8px;
      }
      paper-menu-button {
        float: right;
        top: -65px;
      }
    `]
  }
}