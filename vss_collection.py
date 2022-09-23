from vspec.model.vsstree import VSSNode
from utils import CodeGeneratorContext
from typing import List
import re
_COLLECTION_SUFFIX = "Collection"
_COLLECTION_REG_EX = r"\w+\[\d+,(\d+)\]"

_TYPE_SUFFIX = "Type"
_DEFAULT_RANGE_NAME = "element"

class VssInstance:
    def __init__(self, name: str, content: List[str], is_range: bool):
        # Content List 
        self.content = content 

        # The name of the Instance
        self.name = name

        # Is a named range flag that will be used to generate 
        # getter function for element by index.
        self.is_range = is_range

class VssCollection:
    def __init__(self, node: VSSNode, ctx: CodeGeneratorContext):
        self.ctx = ctx
        self.name = f"{node.name}{_COLLECTION_SUFFIX}"
        self.content_list = self.__gen_collection(node)
    
    def __parse_instances(self, reg_ex, instance) -> VssInstance:
        result = list()

        # parse string instantiation elements (e.g. Row[1,5])
        range_name = _DEFAULT_RANGE_NAME
        if isinstance(instance, str):
            if re.match(reg_ex, instance):
                inst_range_arr = re.split(r"\[+|,+|\]", instance)
                range_name = inst_range_arr[0]
                lower_bound = int(inst_range_arr[1])
                upper_bound = int(inst_range_arr[2])
                for element in range(lower_bound, upper_bound + 1):
                    result.append(f"{range_name}{element}")

                return VssInstance(range_name, result, True)

            raise ValueError("", "", f"instantiation type {instance} not supported")

        # Use list elements for instances (e.g. ["LEFT","RIGHT"])
        if isinstance(instance, list):
            for element in instance:
                result.append(f"{element}")
            return VssInstance(range_name, result, False)

        raise ValueError("", "", f"is of type {type(instance)} which is unsupported")
    
    def __gen_collection_types(self, name, instances) -> tuple[str, list]:
        _type_name = f"{name}{_TYPE_SUFFIX}"
        result = list()
        print(f"{' ' * 5}- {_type_name:25}{instances}")
        result.append(f"{self.ctx.tab}class {_type_name}:")
        result.append(f"{self.ctx.tab * 2}def __init__(self):")
                    
        for instance in instances:
            result.append(f"{self.ctx.tab * 3}self.{instance} = {name}(self)")

        return (_type_name, result)

    def __gen_getter(self, name, instances, indent_level) -> List[str]:
        result = list()
        count = len(instances)
        result.append(f"\n{self.ctx.tab * indent_level}def {name}(self, index: int):")
        result.append(f"{self.ctx.tab * (indent_level + 1)}if index < 1 or index > {count}:")
        result.append(f"{self.ctx.tab * (indent_level + 2)}raise IndexError(f\"Index {{index}} is out of range\")")
       
        result.append(f"{self.ctx.tab * (indent_level + 1)}_options = {{")
        for i in range(len(instances)):
            result.append(f"{self.ctx.tab * (indent_level + 2)}{i + 1} : self.{instances[i]},")
        result.append(f"{self.ctx.tab * (indent_level + 1)}}}")
        
        result.append(f"{self.ctx.tab * (indent_level + 1)}return _options.get(index)\n")
        return result

    def __gen_collection(self, node: VSSNode) -> List[str]:
        print(f"- {self.name:30}{node.instances}")
        result = list()
        result.append(f"class {self.name}:")
        result.append(f"{self.ctx.tab}def __init__(self):")

        complex_list = False
        for instance in node.instances:
            if isinstance(instance, list) or re.match(_COLLECTION_REG_EX, instance):
                complex_list = True

        vss_instance = None
        instance_list_len = len(node.instances)
        instance_type = f"{node.name}"
        has_inner_types = False
        if complex_list:
            # Complex Instances collection 
            vss_instance = self.__parse_instances(_COLLECTION_REG_EX, node.instances[0])

            # if instance_list_len = 1:
            #   -> Flat instance type (list of single instance type). E.g ['Sensor[1,8]']
            # if instance_list_len > 1
            #   -> Multi-level (nested) instance type. E.g ['Row[1,2]', ['Left', 'Right']]
            if instance_list_len > 1:
                instance_type = f"self.{node.name}{_TYPE_SUFFIX}"
                has_inner_types = True

        else:
            # Simple instance type (list object). E.g. Row[1,4] or ['Low', 'High']
            vss_instance = self.__parse_instances(_COLLECTION_REG_EX, node.instances)
            
        instance_list = vss_instance.content
        for instance in instance_list:
            result.append(f"{self.ctx.tab * 2}self.{instance} = {instance_type}(self)")
        # add getter
        result.extend(self.__gen_getter(vss_instance.name, instance_list, 1))

        # Parse Inner types
        if has_inner_types:
            # add inner types
            vss_inner_instance = self.__parse_instances(_COLLECTION_REG_EX, node.instances[1])
            inner_instances = vss_inner_instance.content
            inner_types = self.__gen_collection_types(node.name, inner_instances)
            result.extend(inner_types[1])
            # add getter
            if vss_inner_instance.is_range:
                result.extend(self.__gen_getter(vss_inner_instance.name, inner_instances, 2))
            else:
                result.extend(self.__gen_getter(_DEFAULT_RANGE_NAME, inner_instances, 2))

        return result