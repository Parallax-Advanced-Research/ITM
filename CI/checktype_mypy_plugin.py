from __future__ import annotations

import typing_extensions as t

import mypy.plugin
import mypy.plugins.common
import mypy.types

if t.TYPE_CHECKING:
    import collections.abc as cx
    import mypy.nodes

def plugin(version: str) -> type[CheckTypePlugin]:
    return CheckTypePlugin

class CheckTypePlugin(mypy.plugin.Plugin):
    def get_class_decorator_hook_2(self, fullname: str) -> cx.Callable[[mypy.plugin.ClassDefContext], bool] | None:
        if fullname == "util.checktype.validate":
            return class_decorator_hook
        return None

def class_decorator_hook(ctx: mypy.plugin.ClassDefContext) -> bool:
    #str_type = ctx.api.named_type("builtins.str")
    #dict_typeinfo = something.lookup_typeinfo("builtins.dict")
    #dict_type = Instance(dict_typeinfo, args)
    # https://stackoverflow.com/questions/77756723/type-hints-for-class-decorator
    # https://stackoverflow.com/questions/77733446/polars-api-registering-and-type-checkers

    # TODO: replace with dict[str, Any] once I figure out how to do it.
    # Actually...can I just do ctx.api.named_type('Input_Dictionary') or 'util.checktype.Input_Dictionary'?
    #instance_dict = ctx.api.named_type('Input_Dictionary')
    #any = mypy.types.AnyType(mypy.types.TypeOfAny.implementation_artifact)
    #instance_dict = any # TODO: for some reason, I can set this to ctx.api.named_type('builtins.str') and it doesn't sound an error
    instance_dict = ctx.api.named_type('builtins.dict') # TODO: dict of type Input_Dictionary
    instance_bool = ctx.api.named_type('builtins.bool')
    args = [
        mypy.nodes.Argument(
            variable=mypy.nodes.Var(name="values", type=instance_dict),
            type_annotation=instance_dict,
            initializer=None,
            kind=mypy.nodes.ArgKind.ARG_POS,
            pos_only=False,
        ),
        mypy.nodes.Argument(
            variable=mypy.nodes.Var(name="print_errors", type=instance_bool),
            type_annotation=instance_bool,
            initializer=None,
            kind=mypy.nodes.ArgKind.ARG_POS,
            pos_only=False,
        ),
    ]

    mypy.plugins.common.add_method_to_class(
        ctx.api,
        cls=ctx.cls,
        name="__init__",
        args=args,
        return_type=mypy.types.NoneType(),
        self_type=ctx.api.named_type(ctx.cls.fullname),
    )
    return True

