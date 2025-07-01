# import asyncio
from typing import Optional
from azure.core.exceptions import ClientAuthenticationError
from msgraph import GraphServiceClient
from msgraph.generated.users.item.mail_folders.item.messages.delta.delta_request_builder import (
    DeltaRequestBuilder,
)
from kiota_abstractions.api_error import APIError
from kiota_abstractions.base_request_configuration import RequestConfiguration


async def getTenantUserList(client: GraphServiceClient):
    try:
        res = await client.users.get()
        users = []
        while True:
            users.extend(
                [
                    {"id": user.id, "display_name": user.display_name}
                    for user in res.value
                ]
            )
            if not res.odata_next_link:
                break
            res = await client.users.with_url(res.odata_next_link)
        return users
    except APIError as e:
        print(f"Error occured when calling getTenantMails: {e.message}")
    except ClientAuthenticationError as e:
        print(
            f"Authentication failed, you might want to check if your client secret is still alive: {e.message}"
        )


async def getTenantMailChangeSet(
    client: GraphServiceClient,
    user_id: str,
    deltalink: Optional[str] = None,
):
    try:
        changes = {"mails": []}

        delta_query = RequestConfiguration(
            query_parameters=DeltaRequestBuilder.DeltaRequestBuilderGetQueryParameters(
                expand="attachments"
            )
        )
        user_deltas_requestor: DeltaRequestBuilder = (
            (
                await client.users.by_user_id(user_id)
                .mail_folders.by_mail_folder_id("inbox")
                .messages.delta.with_url(deltalink)
            )
            if deltalink
            else (
                await client.users.by_user_id(user_id)
                .mail_folders.by_mail_folder_id("inbox")
                .messages.delta
            )
        )

        res = await user_deltas_requestor.get(delta_query)

        while True:
            changes["mails"].extend(
                [
                    {
                        "id": mail.id,
                        "subject": mail.subject,
                        "@removed": mail.additional_data.get("@removed"),
                        "attachments": (
                            [
                                {"id": attachment.id, "name": attachment.name}
                                for attachment in mail.attachments
                            ]
                            if mail.attachments
                            else None
                        ),
                    }
                    for mail in res.value
                ]
            )
            if res.odata_delta_link:
                changes["delta_link"] = res.odata_delta_link
                break
            res = await user_deltas_requestor.with_url(res.odata_next_link).get(
                delta_query
            )
        return changes
    except APIError as e:
        print(f"Error occured when calling getTenantMails: {e.message}")
    except ClientAuthenticationError as e:
        print(
            f"Authentication failed, you might want to check if your client secret is still alive: {e.message}"
        )


async def getEMLByMessageId(client: GraphServiceClient, user_id: str, message_id: str):
    try:
        content = (
            await client.users.by_user_id(user_id)
            .messages.by_message_id(message_id)
            .content.get()
        )
        return content
    except APIError as e:
        print(f"Error occured when calling getTenantMails: {e.message}")
    except ClientAuthenticationError as e:
        print(
            f"Authentication failed, you might want to check if your client secret is still alive: {e.message}"
        )


async def getUserMails(client: GraphServiceClient, user_id: str):
    try:
        mails = []
        user_message_requestor = (
            client.users.by_user_id(user_id)
            .mail_folders.by_mail_folder_id("inbox")
            .messages.delta
        )
        user_message_query = RequestConfiguration(
            query_parameters=DeltaRequestBuilder.DeltaRequestBuilderGetQueryParameters(
                expand=["attachments"], change_type="created"
            )
        )
        res = await user_message_requestor.get(user_message_query)
        while True:
            mails.extend(
                [
                    {
                        "id": message.id,
                        "subject": message.subject,
                        "attachments": [
                            {"id": attachment.id, "name": attachment.name}
                            for attachment in message.attachments
                        ],
                    }
                    for message in res.value
                ],
            )
            if not res.odata_next_link:
                break
            res = await user_message_requestor.with_url(res.odata_next_link).get(
                user_message_query
            )
        return mails
    except APIError as e:
        print(f"Error occured when calling getUserMails: {e.message}")
    except ClientAuthenticationError as e:
        print(
            f"Authentication failed, you might want to check if your client secret is still alive: {e.message}"
        )


async def getTenantAllMails(client: GraphServiceClient):
    try:
        users = await getTenantUserList(client)
        users_with_mails = []

        for user in users:
            mails = await getUserMails(client, user["id"])
            users_with_mails.append(
                {
                    "user_id": user["id"],
                    "mails": mails,
                }
            )
        return users_with_mails
    except APIError as e:
        print(f"Error occured when calling getTenantAllMails: {e.message}")
    except ClientAuthenticationError as e:
        print(
            f"Authentication failed, you might want to check if your client secret is still alive: {e.message}"
        )


async def deleteMail(client: GraphServiceClient, user_id: str, message_id: str):
    try:
        await (
            client.users.by_user_id(user_id).messages.by_message_id(message_id).delete()
        )
    except APIError as e:
        print(f"Error occured when calling getTenantMails: {e.message}")
    except ClientAuthenticationError as e:
        print(
            f"Authentication failed, you might want to check if your client secret is still alive: {e.message}"
        )


async def deleteAtt(
    client: GraphServiceClient, user_id: str, message_id: str, attachment_id: str
):
    try:
        await (
            client.users.by_user_id(user_id)
            .messages.by_message_id(message_id)
            .attachments.by_attachment_id(attachment_id)
            .delete()
        )
    except APIError as e:
        print(f"Error occured when calling getTenantMails: {e.message}")
    except ClientAuthenticationError as e:
        print(
            f"Authentication failed, you might want to check if your client secret is still alive: {e.message}"
        )
