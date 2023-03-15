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
  InputBlock,
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
  } = { id: "button", value: "" }
): ButtonType => ({
  type: "button",
  text: Text(text),
  value,
  action_id: id,
  style,
  url,
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
  id,
  okLabel,
}: {
  title: string;
  blocks: any[];
  id?: string;
  okLabel?: string;
}): ModalView => ({
  type: "modal",
  callback_id: id,
  title: Text(title),
  blocks,
  submit: okLabel ? Text(okLabel) : undefined,
});

export const TextInput = ({
  id,
  label,
  placeholder,
  hint,
  multiline,
}: {
  id: string;
  label: string;
  placeholder?: string;
  hint?: string;
  multiline?: boolean;
}): InputBlock => ({
  type: "input",
  block_id: id,
  label: Text(label),
  element: {
    type: "plain_text_input",
    placeholder: placeholder ? Text(placeholder) : undefined,
    multiline,
  },
  hint: hint ? Text(hint) : undefined,
});
