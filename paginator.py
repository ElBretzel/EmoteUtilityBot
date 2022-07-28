import asyncio
import re
import logging
from abc import ABC, abstractmethod, abstractproperty
from collections.abc import Iterable

import emoji
import discord
from discord.errors import NotFound

from constants import MAX_SIZE

ARROW = {"left": "◀", 
         "right": "▶", 
         "stop": "❌",
         "valid": "✅"}
NUM = ("1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟")

class AbstractPaginatorBuilder(ABC):
    
    @abstractproperty
    def prefix(self):
        pass
    
    @abstractproperty
    def reset(self):
        pass

    @abstractmethod
    def base_embed_create(self):
        pass

    @abstractmethod
    async def paginator_store(self):
        pass

    @abstractmethod
    def content_builder(self):
        pass
    
    @abstractmethod
    def _custom_builder(self):
        pass
    
    @abstractmethod
    def _custom_paginator_builder(self):
        pass

    @abstractproperty
    def _format_content_builder(self):
        pass

    @abstractproperty
    def _content_arrangement(self):
        pass


class PaginatorBuilder(AbstractPaginatorBuilder):
    def __init__(self):
        self.reset

        self.separator = ""
        self.decorator = ""
        self._content = []
        self.max_content = 10  # * Max element in one page (not characters)
        self.timeout = 60

        self.embed_content_index = 0
        self.paginator_description = ""

    @property
    def content(self) -> list:
        return self._embed_content
    
    @content.setter
    def content(self, value: list) -> None:
        """
        content(self, value)
        
        Set the content of the paginator

        Parameters
        ----------
        value : list
            The content splitted after each element in the list
            
        Returns
        ----------
        None
        
        Examples
        ----------
        >>> paginator.builder.content = ['Apple', 'Banana', 'Orange']
        """
        self._embed_content = value

    @property
    def prefix(self) -> str:
        return self._prefix

    @prefix.setter
    def prefix(self, new_prefix: object) -> None:
        """
        prefix(self, new_prefix)
        
        Set the prefix before each contents in the paginator.
        
        You need to call this method before building your paginator.

        Parameters
        ----------
        new_prefix : object
            The prefix can be a string or an iterable
            
        Notes
        ----------
        If the prefix is an iterable, the maximum content in a paginator's page
        will be the len of the new prefix.
        
        There is 3 different prefix's template:\n
        /number/ : The prefix will be a range of integer from 1 to 10.\n
        /emote/ : The prefix will be a range of emotes which represent integer from 1 to 10.\n
        /custom/ : You can set the new format of the content during the building method.\n
            
        Returns
        ----------
        None
        
        Examples
        ----------
        >>> paginator.builder.prefix = "*"
        >>> paginator.builder.prefix = ['>', '!', 'x', '🤖']
        >>> paginator.builder.prefix = "/number/"
        >>> paginator.builder.prefix = "/custom/"
        
        """

        if isinstance(new_prefix, str):
            self._prefix = new_prefix
        elif isinstance(new_prefix, Iterable):
            self.max_content = len(new_prefix)  # * To split the paginator
            self._prefix = tuple(new_prefix)  # * Make the prefix immutable
        else:
            self._prefix = str(new_prefix)  # * Avoid bare int or float prefix

    @property
    def reset(self) -> None:
        """
        reset(self)
        
        Reset the builder and all its stored data.

        Returns
        ----------
        None
        
        Examples
        ----------
        >>> paginator.builder.reset()
        
        """
        self.manager = PaginatorManager()  # * New paginator manager

    def paginator_store(self) -> None:
        """
        paginator_store(self)
        
        Store your paginator into your paginator controller.

        This step is required before creating your paginator.
        
        Returns
        ----------
        None
        
        Examples
        ----------
        >>> paginator.builder.paginator_store()
        
        """
        assert isinstance(self.base_embed, discord.Embed), "Error, the base embed is not created."
        assert self._content, "Error, there is no content in the paginator."
        self.manager._add(self.__dict__)  # ? Add in the paginator the final result as a dictionnary

    def base_embed_create(self, name: str, description: str, colour: discord.Colour, **kwargs) -> None:
        """
        base_embed_create(self, name, description, colour)
        
        Create the embed inside your paginator.
        
        You need to call this method before storing your paginator.

        Parameters
        ----------
        name : str
            The main title of the embed.
        description : str
            The main description of the embed.
        colour : discord.Colour
            The colour around the embed.
            
        **field : list, optionnal
            First value is the name of the field (str), then the value (str) and finally the alignement (bool).
        **paginator_description : str, optionnal
            The text above the content of the paginator.
        **image : discord.File, optionnal
            The image displayed under the paginator.
            
        Notes
        ----------
        Each fields must be wrapped around a list or a tuple.
        
        Returns
        ----------
        None
        
        Examples
        ----------
        >>> paginator.builder.base_embed_create("Embed title", "Embed description", discord.Colour.random(),
                                    field=[["Title 1", "Value 1", False], ["Title 2", "Value 2", False]],
                                    paginator_description="Here is my content:")
        """

        assert isinstance(name, str), "The name argument must be a string"
        assert isinstance(description, str), "The description argument must be a string"
        assert isinstance(colour,
                          discord.Colour), "The colour argument must be a colour method from discord.Colour class"

        embed = discord.Embed(title=name,
                              description=description,
                              colour=colour)

        index = 0
        
        if kwargs.get("field"):
            for i, f in enumerate(kwargs["field"]):
                embed.add_field(name=f[0], value=f[1], inline=f[2])
            
            index = i + 1
            
        if kwargs.get("image"):
            embed.set_image(url=f"attachment://{kwargs['image']}")

        embed.add_field(name=".", value=".", inline=False)  # * Create empty field to fill later (paginator content)
        self.paginator_description = kwargs.get("paginator_description")  # * Empty field description
        self.embed_content_index = index  # * Empty field index
        self.base_embed = embed

    def content_builder(self, **kwargs: object) -> None:
        r"""
        content_builder(self, **kwargs)

        This function build and format the content in the paginator.

        You need to call this method before storing the paginator and after setting the prefix.

        Parameters
        ----------
        **separator : str, optionnal
            The separator between each element (eg: foo, bar, ...    ', ' is the separator).
        **decorator : str, optionnal
            The decorator after the prefix (eg: * -> foo, * -> bar, ...    ' -> ' is the decorator (and '*' is the pefix))
        **format : str, optionnal
            Specify only if the prefix is set to /custom/ .
            To customize the content, you need to specify wanted token and set you own value.
            Available tokens: '[PREFIX]="" [DECORATOR]="" [CONTENT] [SEPARATOR]="" .
            
        Notes
        ----------
        You can specify the token in any order.
        If you dont specify the equal sign (eg: [CONTENT]) after a token, it will keep the default value.
        If you dont specify value after the "", it will keep the default value.
        If you dont write a token, it will leave blank the value of the token (eg: if you dont specify the CONTENT's token, it will not display the content).
        If you set any value in the CONTENT's token, the value will be split after each space.

        Returns
        ----------
        None
        
        Raises
        ----------
        ValueError
            The error is raised if the prefix is not specified
            
        Examples
        ----------
        >>> paginator.builder.content_builder()
        >>> paginator.builder.content_builder(separator="\n")
        >>> paginator.builder.content_builder(format='[PREFIX]="O " [DECORATOR]="  ⬌    " [CONTENT]  [SEPARATOR]="\n"')
        >>> paginator.builder.content_builder(format='[CONTENT] [SEPARATOR]="\n"')
        >>> paginator.builder.content_builder(separator="\n", format='[CONTENT] [SEPARATOR]')
        """

        
        try:
            self.prefix
            self.content
        except AttributeError:
            logging.error("You must set the prefix and the content of the builder with the prefix and content method of the PaginatorBuilder class.")
            raise AttributeError("You must set the prefix and the content of the builder with the prefix and content method of the PaginatorBuilder class.")
            

        self.separator = kwargs.get("separator", "\n")  # ? Default separator is ', '
        self.decorator = kwargs.get("decorator"," ")  # ? Default decorator

        if self.prefix == "/custom/":
            self.decorator, self.separator = self._custom_builder(
                kwargs.get("format"))  # ? Return the value after the decorator et separator token


###################################################################################################################
###################################################################################################################

        if self.prefix in ["/number/", "/emote/"]:  # * To avoid long embed
            self.max_content = 10 if isinstance(self.prefix, str) else len(self.prefix) if len(
                self.prefix) <= 10 else 10
        elif self.separator == "\n":
            self.max_content = len(self.prefix) if len(self.prefix) <= self.max_content and not isinstance(self.prefix, str) else self.max_content

###################################################################################################################
###################################################################################################################

        self._content = self._format_content_builder  # ? Build the content of the paginator according to the current setup
    
    def _custom_builder(self, format_: str) -> tuple:
        if not format_:
            raise ValueError("You need to specify the format of the paginator in the content_builder method of PaginatorBuilder class. Please refer to the documentation.")

        new_format = self._custom_paginator_builder(
            format_)  # ? Return a dictionnary with as key the token and as value its value

        decorator = ""
        separator = ""

        if isinstance(new_format.get("PREFIX"), str) and new_format[
            "PREFIX"]:  # * If PREFIX token is filled, self.prefix replaced
            self.prefix = new_format["PREFIX"]
        elif new_format.get("PREFIX") is None:  # * If the PREFIX token is not specified, leave blank
            self.prefix = ""

        if isinstance(new_format.get("CONTENT"), str) and new_format[
            "CONTENT"]:  # * If CONTENT token is filled, edit the embed_content variable
            self._embed_content = new_format["CONTENT"].split(" ")
        elif new_format.get("CONTENT") is None:  # * If the CONTENT token is not set, return empty paginator
            self._embed_content = []

        if isinstance(new_format.get("DECORATOR"), str):
            decorator = new_format["DECORATOR"]

        if isinstance(new_format.get("SEPARATOR"), str):
            separator = new_format["SEPARATOR"]

        return decorator, separator
    
    def _custom_paginator_builder(self, format_: str) -> dict:
        custom_format = re.findall(r'(?:\[(\w*)\](?:="(\n?\t?.*?)")?)', format_)  # ? Ckeck the pattern : [ANY]=?("ANY")?
        return {token: value for token, value in custom_format}

    @property
    def _format_content_builder(self) -> list:
        prefix = self.prefix or ""
        content = self._content_arrangement  # ? Return a list of list with as column the page and as row the content of the paginator
        copy_content = content[:]  # * Create a copy of content to edit

        for page_index, page in enumerate(content):
            for index_content in range(len(page)):
                if prefix == "/number/":
                    copy_content[page_index][
                        index_content] = f"**{index_content + 1}**{self.decorator}{page[index_content]}{self.separator if len(page) - 1 != index_content else ''}"  # * if the element is the last of its page, doesn't add separator
                elif prefix == "/emote/":
                    copy_content[page_index][
                        index_content] = f"**{NUM[index_content]}**{self.decorator}{page[index_content]}{self.separator if len(page) - 1 != index_content else ''}"  # * NUM is list of number emote
                elif isinstance(prefix, str):  # * If the prefix is not an iterable
                    copy_content[page_index][
                        index_content] = f"{prefix}{self.decorator}{page[index_content]}{self.separator if len(page) - 1 != index_content else ''}"
                else:  # * If the prefix is an iterable, iterate through the prefix
                    copy_content[page_index][
                        index_content] = f"{prefix[index_content]}{self.decorator}{page[index_content]}{self.separator if len(page) - 1 != index_content else ''}"
        return tuple(tuple(i) for i in copy_content)  # * Return an immutable

    @property
    def _content_arrangement(self) -> list:

        n_page = 0  # * Number of page in the embed (n - 1)
        n_char_cache = 0  # * Number of characters in a group of strings
        list_content = [[]]  # * Row represent the content in a single page and the column represent the page

        line_jump = 0

        for content in self._embed_content:
            n_char_cache += len(str(content))  # * Add the number of characters in the string
            list_content[n_page].append(
                content)  # * Add the content in a list of list which represent the final embed content.
            line_jump += 1
            if n_char_cache >= MAX_SIZE or (line_jump + 1) % self.max_content == 0:  # * Check if a exceed max character in a message or if there is x content in the page
                line_jump = 0
                n_char_cache = 0  # * Reset the cache of character
                list_content.append([])  # * Add another page
                n_page += 1  # * Set the index for the new page
            

        return [i for i in list_content if i]  # * Clear empty page


class PaginatorManager:
    def __init__(self):
        self.reset_paginator

    def _add(self, paginator: dict) -> None:
        self.paginators.append(paginator)

    @property
    def next_paginator(self) -> dict:
        """
        next_paginator(self)

        Retrieve the next stored paginator.
        
        If the main paginator is static, each page represent a paginator.
        
        Returns
        ----------
        dict
            Dict format of the next paginator.

        Raises
        ----------
        ValueError
            Raise an error if there is no other page.

        Examples
        ----------
        >>> paginator.manager.next_paginator
        """
        if self.paginator_index < len(self.paginators) - 1:
            self.paginator_index += 1
            return self.paginators[self.paginator_index]
        raise ValueError("There is no more paginator.")

    @property
    def previous_paginator(self) -> dict:
        """
        previous_paginator(self)

        Retrieve the previous stored paginator.
        
        If the main paginator is static, each page represent a paginator.
        
        Returns
        ----------
        dict
            Dict format of the previous paginator.

        Raises
        ----------
        ValueError
            Raise an error if there is no previous page.

        Examples
        ----------
        >>> paginator.manager.previous_paginator
        """
        
        if self.paginator_index > 0:
            self.paginator_index -= 1
            return self.paginators[self.paginator_index]
        raise ValueError("This is already the first paginator.")

    @property
    def current_paginator(self) -> dict:
        """
        current_paginator(self)

        Retrieve the current stored paginator.
        
        If the main paginator is static, each page represent a paginator.
        
        Returns
        ----------
        dict
            Dict format of the current paginator.

        Examples
        ----------
        >>> paginator.manager.current_paginator
        """
        return self.paginators[self.paginator_index]
    
    @property
    def reset_paginator(self) -> None:
        self.paginators = []
        self.paginator_index = 0
        self.paginator_detection_desc = ""
        
    def __delitem__(self, key):
        self.paginators.remove(key)
        
    def __getitem__(self, key):
        self.paginators[key]
        
    def __setitem__(self, key, value):
        self.paginators[key] = value
        

class PaginatorController:
    def __init__(self, client: discord.Client, user: discord.User, channel: discord.TextChannel):
        self.client = client
        self.user = user
        self.channel = channel
        
        self._builder = None
        self._manager = None
        self._message = None
        self._valid = 0
        
    def _reset(self):
        self.index = -1
        self.page = 0
        
    @property
    def validation(self) -> bool:
        return self._valid
    
    @validation.setter
    def validation(self, value: bool) -> None:
        """
        validation(self, value)
        
        If the paginator need a validation reaction.

        Parameters
        ----------
        value : bool
            True if the reaction is shown else False
            
        """
        assert isinstance(value, bool), "The value must be a boolean."
        self._valid = value

    @property
    def builder(self) -> AbstractPaginatorBuilder:
        return self._builder

    @builder.setter
    def builder(self, builder: AbstractPaginatorBuilder) -> None:
        """
        builder(self, builder)
        
        Set the paginator's builder instance.
        
        You must set the builder to create the paginator.

        Parameters
        ----------
        builder : AbstractPaginatorBuilder
            The builder instance
            
        Notes
        ----------
        The paginator manager will be automaticly retrieve.
            
        Returns
        ----------
        None
            
        Examples
        ----------
        >>> paginator.builder = PaginatorBuilder()
        """
        self._builder = builder
        self._manager = builder.manager

    @property
    def message(self) -> discord.Message:
        return self._message

    @message.setter
    def message(self, message: discord.Message) -> None:
        """
        message(self, message)

        You can specify a message (sent by the bot) where the paginator will be displayed.

        Parameters
        ----------
        message : discord.Message
            The message must be sent by the bot.
            
        Notes
        ----------
        If you don't specify a message, a new message will be created.
        
        Returns
        ----------
        None
        
        Examples
        ----------
        >>> paginator.message = await paginator.channel.fetch_message(0123456789)
        
        """
        self._message = message
        

    async def paginator_emote(self) -> str:
        """
        paginator_emote(self)
        
        The paginator will set reactions under the message according to the prefix set during the building steps.
        
        To call this method, the prefix must be an iterable or a valid discord emoji.
        
        Notes
        ----------
        If the user close the paginator, return a False bool.

        Returns
        ----------
        str
            The value of the content (after the decorator and before the separator).

        Raises
        ----------
        AttributeError
            Raise an error if the prefix can't be a discord reaction.
        asyncio.TimeoutError
            Raise an error if the user takes more than 1 minute to react.
            
        Examples
        ----------
        >>> result = paginator.paginator_emote()
        """
        self._reset()
        self.paginator_detection_desc = "Détection **d'emotes de navigation** et **d'emotes de réaction**."
        paginator = self._manager.current_paginator # ? Retrieve the dict object of the current Paginator builder
        prefix = paginator["_prefix"]
        if prefix in ["/number/", "/emote/"]:
            prefix = NUM # * The list of number emote
        elif isinstance(prefix, str):
            raise AttributeError("The prefix is not an list or a tuple.")
        else:
            prefix = self.__check_if_emote(prefix) # ? Get the list of corrected emoji format

        task = [asyncio.ensure_future(self._loop_paginator(paginator, type="emote", other=prefix))]
        done, _ = await asyncio.wait(task,
                                     return_when=asyncio.FIRST_COMPLETED) # ? Wait until the paginator close or until the user react the prefix of a content 
        for d in done:
            return d.result()

    async def paginator_message(self) -> str:
        """
        paginator_message(self)
        
        The user can choose a content according to its position in the paginator.
        
        Notes
        ----------
        If the user close the paginator, return a False bool.

        Returns
        ----------
        str
            The value of the content (after the decorator and before the separator).

        Raises
        ----------
        asyncio.TimeoutError
            Raise an error if the user takes more than 1 minute to react.
            
        Examples
        ----------
        >>> result = paginator.paginator_message()
        """
        self._reset()
        self.paginator_detection_desc = "Détection **d'emotes de navigation** et des **messages** envoyés. Le message doit être **un chiffre** donnant **la position** de votre choix **dans la page**."
        paginator = self._manager.current_paginator # ? Retrieve the dict object of the current Paginator builder
        task = [asyncio.ensure_future(self._loop_paginator(paginator, type="message"))]
        done, _ = await asyncio.wait(task,
                                     return_when=asyncio.FIRST_COMPLETED) # ? Wait until the paginator close or until the user write the position of a content 
        for d in done:
            return d.result()
        
    async def paginator_static(self) -> str:
        """
        paginator_static(self)
        
        The user can only switch pages
        
        Notes
        ----------
        If the user close the paginator, return a False bool.

        Returns
        ----------
        str
            The value of the content (after the decorator and before the separator).

        Raises
        ----------
        asyncio.TimeoutError
            Raise an error if the user takes more than 1 minute to react.
            
        Examples
        ----------
        >>> result = paginator.paginator_message()
        """
        self._reset()
        self.paginator_detection_desc = "Détection **d'emotes de navigation** uniquement."
        paginator = self._manager.current_paginator # ? Retrieve the dict object of the current Paginator builder
        task = [asyncio.ensure_future(self._loop_paginator(paginator))]
        done, _ = await asyncio.wait(task,
                                     return_when=asyncio.FIRST_COMPLETED) # ? Wait until the paginator close or until the user write the position of a content 
        for d in done:
            return d.result()

    async def paginator_recursive(self) -> str:
        """
        paginator_recursive(self)
        
        The paginator will be static, the paginator's content will only be displayed.
        
        If there is multiple paginator in the manager, each page represent a paginator.
        
        Notes
        ----------
        This feature is not implemented yet.

        Returns
        ----------
        str
            The value of the content (after the decorator and before the separator).

        Raises
        ----------
        NotImplementedError
            This type of paginator will be implemanted later.
            
        Examples
        ----------
        >>> paginator.paginator_recursive()
        
        """
        self._reset()
        raise NotImplementedError   

    def __check_if_emote(self, value: list) -> list:

        _corrected_list = []
        for v in value:

            foo = re.findall(r"(<?:[A-zÀ-ÿ0-9\\-_&.’”“()!#\\*+?–]+:(?:(\d+)>))",
                             v)  # * Find if the string is in the format <:NAME:ID>

            if emoji.emoji_count(v): # * If the value is bare emoji
                _corrected_list.append(emoji.emoji_lis(v)[0]["emoji"]) # * Fetch the first emoji in the string
            elif foo: # * If the value is in the format <:NAME:ID>
                _corrected_list.append(v)
            else: # * If the value is not an emoji
                raise AttributeError("The prefix is not a valid discord emoji.")

        return _corrected_list

    async def _loop_paginator(self, paginator: dict, **kwargs) -> str:

        previous_page = len(paginator["_content"]) # * Use to avoid a flood of reaction | check if a reaction is already set | here, it will set all the reactions
        while True:
            logging.debug("Setting content")
            self._set_paginator_content(paginator) # ? Edit the embed and set the content in the paginator
            logging.debug("Setting footer")
            self._set_paginator_footer(paginator) # ? Edit the embed and set the footer
            logging.debug("Setting message")
            await self._set_message(paginator) # ? Send or edit the message
            logging.debug("Setting arrow")
            arrow = await self._set_nav_reactions(paginator, previous_page, **kwargs) # ? Use the arrow to navigate between pages/paginators. If the paginator detects prefix's emotes, sets the reactions of the page.
            logging.debug("Setting wait for events")
            done_task, pending_task = await self._paginator_wait_for(nav=arrow, paginator=paginator, **kwargs) # ? Wait until any reaction by the user
            logging.debug("Setting the task controller")
            task_result = await self._control_tasks(done_task, pending_task) # ? Check the result of the task
            if not task_result: break # * If the task return an error or nothing
            logging.debug("Setting page manipulation")
            previous_page = self.page # * avoid to add previously set nav reaction
            if isinstance(task_result, tuple): # * If the user react with a reaction
                if task_result[0].emoji == ARROW["stop"]:
                    logging.debug("Stop reaction used")
                    try:
                        await self.message.clear_reactions()
                    except discord.errors.Forbidden:
                        pass
                    return False
                elif task_result[0].emoji == ARROW["right"]:
                    logging.debug("Right reaction used")
                    self.page += 1
                elif task_result[0].emoji == ARROW["left"]:
                    logging.debug("Left reaction used")
                    self.page -= 1
                elif task_result[0].emoji == ARROW["valid"]:
                    logging.debug("Valid reaction used")
                    try:
                        await self.message.clear_reactions()
                    except discord.errors.Forbidden:
                        pass
                    return "V"
                else:
                    logging.debug("Reaction sent")
                    return await self._get_final_data(result=task_result[0].emoji, paginator=paginator, **kwargs) # ? Get the value of the content between the decorator and the separator
            else:
                logging.debug("Message sent")
                try:
                    await task_result.delete()
                except (NotFound, discord.errors.Forbidden):
                    pass
                return await self._get_final_data(result=task_result.content, paginator=paginator, **kwargs)  # ? Get the value of the content between the decorator and the separator


    async def _paginator_wait_for(self, **kwargs) -> tuple:
        reactions = kwargs.get("nav")  # * List of reaction
        paginator = kwargs.get("paginator")

        if kwargs.get("type") == "emote":
            reactions.extend(kwargs["other"]) # * Add the prefix's emotes in the emote detection
        if self.validation:
            reactions.append(ARROW["valid"])

        def check_reaction(reaction: discord.Reaction, user: discord.User) -> bool:  # * basic check for reaction
            return (reaction.message.id == self.message.id and
                    str(reaction.emoji) in reactions and user.id == self.user.id)

        def check_message(message: discord.Message) -> bool:  # * check if message is in the range of the number of content in one page
            return message.channel.id == self.channel.id and self.user.id == message.author.id and message.content.isdigit() \
                   and (message.content in [str(i) for i in range(1, len(paginator["_content"][self.page]) + 1)])

        if kwargs.get("type") == "message":

            pending_tasks = [self.client.wait_for('message', timeout=paginator["timeout"], check=check_message),
                             self.client.wait_for('reaction_add', timeout=paginator["timeout"], check=check_reaction)]

            done_task, pending_task = await asyncio.wait(pending_tasks,
                                                         return_when=asyncio.FIRST_COMPLETED)  # * Check both if the user react with a reaction or with a message
            return done_task, pending_task
        else:
            pending_tasks = [self.client.wait_for('reaction_add', timeout=paginator["timeout"], check=check_reaction)]
            done_task, pending_task = await asyncio.wait(pending_tasks, return_when=asyncio.FIRST_COMPLETED) # * Check if the user react with a message
            return done_task, pending_task

    async def _control_tasks(self, done_task: asyncio.Task, pending_task: asyncio.Task) -> object:

        if pending_task: # * If there is another pending task, cancel it
            for p_task in pending_task:
                p_task.cancel()

        for d_task in done_task:
            try:
                task_result = d_task.result()
            except asyncio.TimeoutError: # * If the user takes more than 1 minute
                try:
                    await self.message.clear_reactions()
                except discord.errors.Forbidden:
                    pass
                return
                
        # ? The result is:
        # * - a tuple if the detection is an emote (1st element is a discord.Reaction object and the 2nd is a discord.Member object)
        # * - a discord.Message object if the detection is a message sent by an user
        
        return task_result 

    async def _set_prefix_reactions(self, paginator: dict, prefix: tuple, previous_page: int) -> None:
        total_content_in_page = lambda p: len(paginator["_content"][p]) # ? Get the len of a paginator page
        for i, r in enumerate(prefix):        
            if i > total_content_in_page(self.page) - 1: # * If the prefix is not in the page
                if previous_page != len(paginator["_content"]):
                    try:
                        await self.message.clear_reaction(r) # * Clear the prefix's reaction
                    except discord.errors.Forbidden:
                        pass
                continue
            elif (
                    previous_page == len(paginator["_content"]) or  # * Check the paginator has just been created
                    (self.page + 1 < len(paginator["_content"]) and  # * Check if there is a next page available
                    i >= total_content_in_page(self.page + 1) and  # * Check the next page dont have same amount of content
                    previous_page > self.page)  # * Check if there is not already a reaction
            ):
                await self.message.add_reaction(r)

    async def _set_nav_reactions(self, paginator: dict, *args, **kwargs) -> list:

        arrow = []

        if kwargs.get("type") == "emote":
            await self._set_prefix_reactions(paginator, prefix=kwargs.get("other"), previous_page=args[0]) # ? Add the prefix emote

        if len(paginator["_content"]) == 1: # * If the paginator has only one page
            pass

        elif self.page == 0:  # * If the paginator is in the first page and has more than 1 page
            logging.debug("First page")
            try:
                await self.message.clear_reaction(ARROW["left"])  # ? Remove unused reaction
            except (NotFound, discord.errors.Forbidden):
                pass
            finally:
                logging.debug("Adding right")
                arrow.append(ARROW["right"])
                await self.message.add_reaction(ARROW["right"])

        elif self.page == len(paginator["_content"]) - 1:  # * If the paginator is in the last page
            logging.debug("Last page")
            try:
                await self.message.clear_reaction(ARROW["right"])  # ? Remove unused reaction
            except (NotFound, discord.errors.Forbidden):
                pass
            finally:
                logging.debug("Adding left")
                arrow.append(ARROW["left"])
                await self.message.add_reaction(ARROW["left"])

        else:  # * If the paginator's current page is located between first and last page
            logging.debug("Betwen two pages")
            logging.debug("Adding right and left")
            arrow.append(ARROW["right"])
            arrow.append(ARROW["left"])
            await self.message.add_reaction(ARROW["left"])
            await self.message.add_reaction(ARROW["right"])

        if self.validation:
            logging.debug("Validation parameter")
            arrow.append(ARROW["valid"])
            await self.message.add_reaction(ARROW["valid"])
        logging.debug("Adding stop")
        arrow.append(ARROW["stop"])
        await self.message.add_reaction(ARROW["stop"])
        logging.debug("Return")
        return arrow

    def _set_paginator_content(self, paginator: dict) -> None:        
        
        paginator_description = f"{paginator['paginator_description']}\n{self.paginator_detection_desc}" if paginator["paginator_description"] else self.paginator_detection_desc

        paginator["base_embed"].set_field_at(paginator["embed_content_index"], name=paginator_description,
                                             value=f''.join(paginator["_content"][self.page]))

    def _set_paginator_footer(self, paginator: dict) -> None:
        paginator["base_embed"].set_footer(
            text=f"• Requête de {self.user} • Page {int(self.page) + 1} / {len(paginator['_content'])}")

    async def _set_message(self, paginator: dict) -> None:
        if not self.message:
            self.message = await self.channel.send(embed=paginator["base_embed"])
        else:

            await self.message.edit(embed=paginator["base_embed"])

    async def _get_final_data(self, result, paginator: dict, **kwargs) -> str:

        if paginator["_prefix"] in ["/number/", "/emote/"] and kwargs.get("type") == "emote":
            index = NUM.index(result) # * Get the index of the result in the list of number emote
        elif kwargs.get("type") == "emote": # * If the paginator detects emote
            index = kwargs.get("other").index(str(result))
        else: # * If the paginator detects message
            index = int(result) - 1
        
        try:
            await self.message.clear_reactions()
        except (NotFound, discord.errors.Forbidden):
            pass
        self.index = index + self.page
        return paginator["_content"][self.page][index].split(paginator["decorator"])[1].split(paginator["separator"])[0]
