import { LitElement, customElement, property, CSSResultArray, css, TemplateResult, html } from "lit-element";
import { HacsStyle } from "../style/hacs-style"
import { HomeAssistant } from "custom-card-helpers";

import { Configuration, Repository } from "../types"


@customElement("hacs-custom-repositories")
export class CustomRepositories extends LitElement {
    @property()
    public hass!: HomeAssistant;

    @property()
    public repositories!: Repository[];

    @property()
    public custom!: Repository[];

    @property()
    public configuration!: Configuration;

    @property()
    public SaveSpinner?: boolean;

    Delete(ev) {
        this.hass.connection.sendMessagePromise({
            type: "hacs/repository",
            action: "delete",
            repository: ev.composedPath()[4].repoID
        }).then(
            (resp) => {
                this.repositories = (resp as Repository[]);
                this.requestUpdate();
            },
            (err) => {
                console.error('Message failed!', err);
            }
        );
    }

    Save(ev) {
        this.SaveSpinner = true;
        console.log(ev.composedPath()[1].children[0].value)
        console.log(ev.composedPath()[1].children[1].selectedItem.category)
        this.hass.connection.sendMessagePromise({
            type: "hacs/repository/data",
            action: "add",
            repository: ev.composedPath()[1].children[0].value,
            data: ev.composedPath()[1].children[1].selectedItem.category
        }).then(
            (resp) => {
                this.repositories = (resp as Repository[]);
                this.SaveSpinner = false;
                this.requestUpdate();
            },
            (err) => {
                console.error('Message failed!', err);
            }
        );
    }

    protected render(): TemplateResult | void {
        this.custom = this.repositories.filter(function (repo) {
            if (!repo.custom) return false;
            return true;
        })

        return html`
        <ha-card header="${this.hass.localize("component.hacs.settings.custom_repositories")}">
            <div class="card-content">
            <div class="custom-repositories-list">

            ${this.custom.sort((a, b) => (a.full_name > b.full_name) ? 1 : -1).map(repo =>
            html`
                <div class="row" .repoID=${repo.id}>
                    <paper-item>
                        ${repo.full_name}
                        <ha-icon
                        title="${(this.hass.localize("component.hacs.settings.delete"))}"
                        class="listicon" icon="mdi:delete"
                        @click=${this.Delete}
                        ></ha-icon>
                    </paper-item>
                </div>
                `)}
            </div>
            </div>

            <div class="card-actions">
                <paper-input class="inputfield" placeholder=${(this.hass.localize("component.hacs.settings.add_custom_repository"))} type="text"></paper-input>


                <paper-dropdown-menu class="category"
                label="${this.hass.localize(`component.hacs.settings.category`)}">
                  <paper-listbox slot="dropdown-content" selected="-1">
                      ${this.configuration.categories.map(category => html`
                      <paper-item .category=${category}>
                        ${this.hass.localize(`component.hacs.common.${category}`)}
                      </paper-item>`)}
                  </paper-listbox>
              </paper-dropdown-menu>

                ${(this.SaveSpinner ? html`<paper-spinner active class="loading"></paper-spinner>` : html`
                <ha-icon title="${(this.hass.localize("component.hacs.settings.save"))}"
                    icon="mdi:content-save" class="saveicon"
                    @click=${this.Save}>
                </ha-icon>
                `)}
            </div>

        </ha-card>
            `;
    }

    static get styles(): CSSResultArray {
        return [HacsStyle, css`
            ha-card {
                width: 90%;
                margin-left: 5%;
            }
            .custom-repositories {

            }

            .add-repository {

            }
            .inputfield {
                width: 60%;
            }
            .category {
                position: absolute;
                width: 30%;
                right: 54px;
                bottom: 5px;
            }
            .saveicon {
                color: var(--primary-color);
                position: absolute;
                right: 0;
                bottom: 24px;
            }
            .listicon {
                color: var(--primary-color);
                right: 0px;
                position: absolute;
            }
            .loading {
                position: absolute;
                right: 10px;
                bottom: 22px;
            }
        `]
    }
}