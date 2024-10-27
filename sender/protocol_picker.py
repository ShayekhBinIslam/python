class ProtocolPicker:
    def __init__(self, memory):
        self.memory = memory

    def get_an_adequate_protocol(self, task_id, eligible_protocols):
        # Will ignore protocols that haven't been downloaded yet

        # First, try with protocols having an implementation
        protocols_with_implementations = [ protocol_id for protocol_id in eligible_protocols if self.memory.protocol_is_adequate(task_id, protocol_id) and self.memory.protocol_has_implementation(task_id, protocol_id) ]

        if len(protocols_with_implementations) > 0:
            print('Found protocol with implementation:', protocols_with_implementations[0])
            return protocols_with_implementations[0]

        # If there is no matching implementation, try with protocols that have been categorized and have been deemed adequate
        adequate_protocols = [ protocol_id for protocol_id in eligible_protocols if self.memory.protocol_is_adequate(task_id, protocol_id) ]

        if len(adequate_protocols) > 0:
            return adequate_protocols[0]
        
        # If there are still none, try with protocols that haven't been categorized yet (but are already in memory), categorize them and check again
        uncategorized_protocols = [protocol_id for protocol_id in eligible_protocols if protocol_id in self.memory.protocols and not self.memory.protocols.is_categorized(task_id, protocol_id)]

        uncategorized_protocols = self.prefilter_protocols(uncategorized_protocols, task_id)

        for protocol_id in uncategorized_protocols:
            suitable = self.categorize_protocol(protocol_id, task_id)

            if suitable:
                return protocol_id

        # We're out of luck, return None
        return None

    def get_suitable_protocol(self, task_id, task_schema):
        return None
        # TODO: Implement once protocol DBs are fully ported 

        # Start by retrieving the protocols that the target node supports
        target_protocols = query_protocols(target_node)
        print('Target protocols:', target_protocols)

        protocol_id = get_an_adequate_protocol(task_type, list(target_protocols.keys()))

        if protocol_id is not None:
            print('Found adequate protocol from storage:', protocol_id)
            return protocol_id

        # If there are none, categorize the remaining target protocols, and try again
        for protocol_id, sources in target_protocols.items():
            if protocol_id not in PROTOCOL_INFOS:
                for source in sources:
                    response = request_manager.get(source, timeout=shared_config('timeout'))
                    protocol_document = response.text

                    metadata = request_manager.get(source.replace('protocol', 'metadata'), timeout=shared_config('timeout')).json()

                    if metadata['status'] != 'success':
                        print('Failed to retrieve metadata:', metadata)
                        continue

                    metadata = metadata['metadata']


                    protocol_data = {
                        'name': metadata['name'],
                        'description': metadata['description'],
                        'protocol': protocol_document
                    }

                    register_new_protocol(protocol_id, source, protocol_data)

        for protocol_id in prefilter_protocols(list(target_protocols.keys()), task_type):
            # Categorize the protocol
            suitable = categorize_protocol(protocol_id, task_type)

            if suitable:
                return protocol_id

        if get_num_conversations(task_type, target_node) < num_conversations_for_protocol:
            # No point in exploring potential protocols (outside of the explicitly supported ones) if we haven't talked enough times with the target
            return None

        # If there are still none, check if we have in our memory a suitable protocol

        protocol_id = get_an_adequate_protocol(task_type, PROTOCOL_INFOS.keys())

        if protocol_id is not None:
            return protocol_id
        
        # If there are still none, check the public protocol database and categorize them
        # Note: in a real system, we wouldn't get all protocols from the database, but rather
        # only the ones likely to be suitable for the task

        public_protocols_response = request_manager.get(get_protocol_db_url(), timeout=shared_config('timeout')).json()

        if public_protocols_response['status'] == 'success':
            public_protocols = [x for x in public_protocols_response['protocols']]
        else:
            public_protocols = []

        print('Stored protocols:', PROTOCOL_INFOS.keys())
        print('Public protocols:', public_protocols)

        for protocol_metadata in public_protocols:
            protocol_id = protocol_metadata['id']
            # Retrieve the protocol
            
            print('Protocol ID:', urllib.parse.quote_plus(protocol_id))

            uri = f'{get_protocol_db_url()}/protocol?' + urllib.parse.urlencode({
                'id': protocol_id
            })
            print('URI:', uri)

            protocol_document_response = request_manager.get(uri, timeout=shared_config('timeout'))

            if protocol_document_response.status_code == 200:
                protocol_document = protocol_document_response.text
                protocol_data = {
                    'name': protocol_metadata['name'],
                    'description': protocol_metadata['description'],
                    'protocol': protocol_document
                }
                register_new_protocol(protocol_id, uri, protocol_data)

        public_protocol_ids = prefilter_protocols([x['id'] for x in public_protocols], task_type)

        for protocol_id in public_protocol_ids:
            # Categorize the protocol
            suitable = categorize_protocol(protocol_id, task_type)

            if suitable:
                return protocol_id
        
        # If there are still none, don't use a protocol
        return None