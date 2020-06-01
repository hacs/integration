# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring,no-member, attribute-defined-outside-init


class RepositoryMethodRegistration:
    async def registration(self, ref=None) -> None:
        self.logger.warning(
            "'registration' is deprecated, use 'async_registration' instead"
        )
        await self.async_registration(ref)

    async def async_registration(self, ref=None) -> None:
        if ref is not None:
            self.data.selected_tag = ref
            self.ref = ref
            self.force_branch = True

        if not await self.validate_repository():
            return False

        # Run common registration steps.
        await self.common_registration()

        # Run local post registration steps.
        await self.async_post_registration()

    async def async_post_registration(self):
        pass
