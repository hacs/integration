import { property } from "lit-element";

import {
    HomeAssistant
} from "custom-card-helpers";

export class HomeAssistantObject extends HTMLElement {
    @property() public hass: HomeAssistant;
}