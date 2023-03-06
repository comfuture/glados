import { ButtonAction } from "@slack/bolt";
import {
  Button as ButtonType,
  ImageBlock,
  ModalView,
  MrkdwnElement,
  PlainTextElement,
  SectionBlock,
  ContextBlock,
  ActionsBlock,
} from "@slack/types";

export const Text = (text: string): PlainTextElement => ({
  type: "plain_text",
  text,
});

export const Markdown = (text: string): MrkdwnElement => ({
  type: "mrkdwn",
  text,
});

// export type ButtonStyle = "default" | "primary" | "danger";

export const Button = (
  text: string,
  {
    id,
    value,
    style,
    url,
  }: {
    id: string;
    value: string;
    style?: "primary" | "danger" | undefined;
    url?: string;
  }
): ButtonType => ({
  type: "button",
  text: Text(text),
  value,
  action_id: id,
  style,
});

export const Image = (
  imageUrl: string,
  altText: string,
  { title }: { title?: PlainTextElement } = {}
): ImageBlock => ({
  type: "image",
  image_url: imageUrl,
  alt_text: altText,
  title,
});

export const Section = ({ ...props }): SectionBlock => ({
  type: "section",
  ...props,
});

export const Context = (elements: any[]): ContextBlock => ({
  type: "context",
  elements,
});

export const Actions = (elements: any[]): ActionsBlock => ({
  type: "actions",
  elements,
});

export const Modal = ({
  title,
  blocks,
}: {
  title: string;
  blocks: any[];
}): ModalView => ({
  type: "modal",
  title: Text(title),
  blocks,
});
