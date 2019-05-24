"""HACS."""


class HACS:
    """The brains of the operation."""
    data = {}
    hass = None
    github = None
    blacklist = []
    elements = []
    task_running = False


    async def add_new_element(self, element):
        """
        Add new element to HACS.

        element: HacsElementIntegration or HacsElementPlugin
        """
        if element not in self.elements:
            self.elements.append(element)
