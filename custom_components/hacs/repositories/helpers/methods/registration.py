# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring,no-member, attribute-defined-outside-init


class RepositoryMethodPreRegistration:
    async def async_pre_registration(self):
        pass


class RepositoryMethodRegistration:
    async def registration(self, ref=None) -> None:
        self.logger.warning(
            "'registration' is deprecated, use 'async_registration' instead"
        )
        await self.async_registration(ref)

    async def async_registration(self, ref=None) -> None:
        # Run local pre registration steps.
        await self.async_pre_registration()

        if ref is not None:
            self.data.selected_tag = ref
            self.ref = ref
            self.force_branch = True

        if not await self.validate_repository():
            return False

        # Run common registration steps.
        await self.common_registration()

        # Set correct local path
        self.content.path.local = self.localpath

        # Run local post registration steps.
        await self.async_post_registration()


class RepositoryMethodPostRegistration:
    async def async_post_registration(self):
        pass
