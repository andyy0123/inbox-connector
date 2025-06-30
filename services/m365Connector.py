# import asyncio
from typing import Optional
from azure.core.exceptions import ClientAuthenticationError
from msgraph import GraphServiceClient
from msgraph.generated.users.item.mail_folders.item.messages.item.message_item_request_builder import (
    MessageItemRequestBuilder,
)
from msgraph.generated.users.item.mail_folders.item.messages.delta.delta_request_builder import (
    DeltaRequestBuilder,
)
from kiota_abstractions.api_error import APIError
from kiota_abstractions.base_request_configuration import RequestConfiguration


async def getTenantUserList(client: GraphServiceClient):
    try:
        res = await client.users.get()
        return [
            {"id": user.id, "display_name": user.display_name} for user in res.value
        ]
    except APIError as e:
        print(f"Error occured when calling getTenantMails: {e.message}")
    except ClientAuthenticationError as e:
        print(
            f"Authentication failed, you might want to check if your client secret is still alive: {e.message}"
        )


async def getTenantMailChangeSet(
    client: GraphServiceClient,
    deltalink: Optional[str] = None,
):
    try:
        users = await getTenantUserList(client)
        changes = []

        for user in users:
            delta_query = RequestConfiguration(
                query_parameters=DeltaRequestBuilder.DeltaRequestBuilderGetQueryParameters(
                    expand="attachments"
                )
            )
            user_deltas = (
                (
                    await client.users.by_user_id(user["id"])
                    .mail_folders.by_mail_folder_id("inbox")
                    .messages.delta.with_url(deltalink)
                    .get(request_configuration=delta_query)
                )
                if deltalink
                else (
                    await client.users.by_user_id(user["id"])
                    .mail_folders.by_mail_folder_id("inbox")
                    .messages.delta.get(request_configuration=delta_query)
                )
            )
            changes.append(
                {
                    "user_id": user["id"],
                    "delta_link": user_deltas.odata_delta_link,
                    "mails": (
                        {
                            "id": mail.id,
                            "subject": mail.subject,
                            "@removed": mail.additional_data.get("@removed"),
                            "attachments": [
                                {"id": attachment.id, "name": attachment.name}
                                for attachment in mail.attachments
                            ]
                            if mail.attachments
                            else None,
                        }
                        for mail in user_deltas.value
                    ),
                }
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


async def getTenantAllMails(client: GraphServiceClient):
    try:
        users = await getTenantUserList(client)
        mails = []

        for user in users:
            mails.append(
                {
                    "user_id": user["id"],
                    "mails": [
                        {
                            "id": message.id,
                            "subject": message.subject,
                            "attachments": [
                                {"id": attachment.id, "name": attachment.name}
                                for attachment in message.attachments
                            ],
                        }
                        for message in (
                            await client.users.by_user_id(user["id"])
                            .mail_folders.by_mail_folder_id("inbox")
                            .messages.get(
                                request_configuration=RequestConfiguration(
                                    query_parameters=MessageItemRequestBuilder.MessageItemRequestBuilderGetQueryParameters(
                                        expand=["attachments"]
                                    )
                                )
                            )
                        ).value
                    ],
                }
            )

        return mails
    except APIError as e:
        print(f"Error occured when calling getTenantMails: {e.message}")
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
