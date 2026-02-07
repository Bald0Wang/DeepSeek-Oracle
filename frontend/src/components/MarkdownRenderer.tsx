import ReactMarkdown from "react-markdown";


interface MarkdownRendererProps {
  content: string;
}


export function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return <ReactMarkdown>{content}</ReactMarkdown>;
}
