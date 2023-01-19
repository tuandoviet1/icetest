import { useToast } from "@chakra-ui/react";
import { getFormattedName } from "/components/TracePage/CallName";
import {
  FlattenedFStringPart,
  flattenFString,
  FString,
  RawFStringPart,
} from "/components/TracePage/FString";
import classNames from "classnames";
import { Component, useMemo } from "react";
import { CaretDown } from "phosphor-react";

type JsonChild =
  | { type: "array"; values: unknown[] }
  | { type: "object"; values: [string, unknown][] }
  | { type: "value"; value: unknown; fstring?: FlattenedFStringPart[] };

const getStructuralType = (data: unknown) => {
  if (typeof data === "object" && data && !Array.isArray(data)) return "object";
  if (Array.isArray(data)) return "array";
  return "value";
};

const TypeIdentifiers = {
  object: <span className="shrink-0 font-mono mr-[8px]">{"{}"}</span>,
  array: <span className="shrink-0 font-mono mr-[8px]">{"[]"}</span>,
  value: null,
};

interface Props {
  values: unknown[];
}

class ArrayRenderer extends Component<Props, number> {
  override render() {
    return this.props.values.map((el, index) => (
      <div key={index} className="mb-1">
        <span className="text-gray-600">{`${index + 1}. `}</span>
        {TypeIdentifiers[getStructuralType(el)]}
        <DetailRenderer data={el} />
      </div>
    ));
  }
}

interface Propz {
  values: [string, unknown][];
}

interface ClickyProps {
  handleClick: () => void;
}

// TODO maybe take out this class now that we have caretdown
class DownArrow extends Component<ClickyProps> {
  override render() {
    return (
      <button>
        <CaretDown onClick={this.props.handleClick} />
      </button>
    );
  }
}

interface IsExpanded {
  [key: string]: boolean;
}

interface Florida {
  // because it's a state
  isExpanded: IsExpanded; // key -> isExpanded
}

// TODO do we need to add down arrows to top level array for array renderer?

// TODO make the structural type use enums instead of strings
// TODO also only present an arrow depending on the number of children
class ObjectRenderer extends Component<Propz, Florida> {
  constructor(props: Propz) {
    super(props);
    // props but make it a dictionary
    this.state = {
      // TODO lol copilot you goof there's probably a better way to do this
      isExpanded: props.values.reduce((acc, [key, _]) => {
        acc[key] = true;
        return acc;
      }, {} as IsExpanded),
    };
  }

  override render() {
    // TODO lift out?
    function isCollapsible(value: unknown): boolean {
      const structuralType = getStructuralType(value);
      if (structuralType === "value") return false;
      if (structuralType === "array") return true;
      if (structuralType === "object") {
        // TODO what about unit testing this
        // TODO what about empty objects
        // TODO what about empty arrays
        // TODO what about empty strings
        // TODO what about objects with the property __fstring__
        const isFString = "__fstring__" in value;
        return !isFString;
      }
      return false;
    }

    return this.props.values.map(([key, value], index) => (
      <div key={index} className="mb-1">
        <span className="text-gray-600">{`${getFormattedName(key)}: `}</span>
        {TypeIdentifiers[getStructuralType(value)]}

        {isCollapsible(value) ? (
          <DownArrow
            handleClick={() =>
              // TODO do we need to use the callback form of setState?
              this.setState(() => {
                // TODO do we need to copy the map? or is it fine to mutate it?
                const newMap = this.state.isExpanded;
                newMap[key] = !this.state.isExpanded[key];
                return { isExpanded: newMap };
              })
            }
          />
        ) : null}
        {this.state.isExpanded[key] ? <DetailRenderer data={value} /> : null}
      </div>
    ));
  }
}

// TODO name maybe should be different
type FStringyData = {
  __fstring__: unknown;
};

function buildViewForFString(data: FStringyData): JsonChild {
  const parts = data.__fstring__ as RawFStringPart[];
  const flattenedParts = flattenFString(parts);
  const value = flattenedParts.map(part => (typeof part === "string" ? part : part.value)).join("");
  return { type: "value", value, fstring: flattenedParts };
}

function buildViewForArrayOrObject(data: object): JsonChild {
  if (Array.isArray(data)) return { type: "array", values: data };
  if ("__fstring__" in data) {
    return buildViewForFString(data);
  }
  return { type: "object", values: Object.entries(data) };
}

function renderForArrayOrObject(view: JsonChild, root?: boolean) {
  // TODO what's a more idiomatic way to handle this? probably with subtyping
  if (view.type !== "array" && view.type !== "object") {
    throw new Error("renderForArrayOrObject called with non-array or non-object");
  }
  return (
    <div className={classNames("flex", root ? undefined : "ml-4")}>
      <div>
        {view.type === "array" ? (
          <ArrayRenderer values={view.values} />
        ) : (
          <ObjectRenderer values={view.values} />
        )}

        {view.values.length === 0 ? <span className="text-gray-600">Empty</span> : null}
      </div>
    </div>
  );
}

function renderForValue(view: JsonChild) {
  const toast = useToast();
  if (view.type !== "value") {
    throw new Error("renderForValue called with non-value");
  }
  const value = `${view.value}`;
  return value ? (
    <span
      className="inline whitespace-pre-wrap"
      onClick={() => {
        navigator.clipboard.writeText(value);
        toast({ title: "Copied to clipboard", duration: 1000 });
      }}
    >
      {view.fstring ? <FString parts={view.fstring} /> : value}
    </span>
  ) : (
    <span className="text-gray-600">empty</span>
  );
}

export const DetailRenderer = ({ data, root }: { data: unknown; root?: boolean }) => {
  const view: JsonChild = useMemo(() => {
    if (typeof data === "object" && data) {
      return buildViewForArrayOrObject(data);
    } // TODO methods and constructors?
    return { type: "value", value: data };
  }, [data]);

  if (view.type === "array" || view.type === "object") {
    return renderForArrayOrObject(view, root);
  }
  return renderForValue(view);
};