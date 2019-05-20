"""Card elements."""


async def overview_card(element, card_icon):
    """Generate a UI card element."""
    return """
      <div class="row">
        <div class="col s12">
          <div class="card blue-grey darken-1">
            <div class="card-content white-text">
              <span class="card-title">
                {name} {card_icon}
              </span>
              <span class="white-text">
                <p>
                  {description}
                </p>
              </span>
            </div>
            <div class="card-action">
              <a href="/community_element/{element}">Manage</a>
            </div>
          </div>
        </div>
      </div>
    """.format(
        card_icon=card_icon,
        name=str(element.name),
        description=str(element.description),
        element=str(element.element_id),
    )


async def warning_card(message, title=None):
    """Generate a warning card."""

    if title is None:
        title = ""
    else:
        title = """
          <h5>
            {}
          </h5></br>
        """.format(
            title
        )

    return """
      <div class="row">
        <div class="col s12">
          <div class="card-panel orange darken-4">
            <div class="card-content white-text">
              {}
              <span>
                {}
              </span>
            </div>
          </div>
      </div>
    """.format(
        title, message
    )


async def info_card(message, title=None):
    """Generate a info card."""

    if title is None:
        title = ""
    else:
        title = """
          <h5>
            {}
          </h5></br>
        """.format(
            title
        )

    return """
      <div class="row">
        <div class="col s12">
          <div class="card-panel" style="background-color: #bbdefb00 !important">
            <div class="card-content black-text">
              {}
              <span>
                {}
              </span>
            </div>
          </div>
      </div>
    """.format(
        title, message
    )
