from opentrons import protocol_api
import requests
def notify_slack(message):
    webhook_url = "INSERT WEB HOOK URL HERE"
    try:
        requests.post(webhook_url, json={"text": f"<@U09MFUW1YCF> {message}"}) ## add your own user ID here
    except Exception as e:
        print(f"<@U09MFUW1YCF> Slack notification failed: {e}")

metadata = {
    'protocolName': 'Vacuum miniprep variable samples',
    'description': 'Miniprep 1-24 samples using 3D printed vacuum manifold. Start with resuspended cells in 2ml tubes.',
    'author': 'JATD'
    }

requirements = {
    "robotType": "Flex",
    "apiLevel": "2.23",
}

def add_parameters(parameters: protocol_api.Parameters):
    parameters.add_int(
        variable_name="num_samples",
        display_name="Number of Samples",
        description="Number of samples to process (1-24)",
        default=24,
        minimum=1,
        maximum=24,
        unit="samples"
    )

def run(protocol: protocol_api.ProtocolContext):
    # Get number of samples from parameters
    num_samples = protocol.params.num_samples
    
    protocol.comment(f"Processing {num_samples} samples")
    
    # Load labware
    tips1 = protocol.load_labware("opentrons_flex_96_tiprack_50ul", location = "A2") 
    tips2 = protocol.load_labware("opentrons_flex_96_tiprack_50ul", location = "C1")
    trash = protocol.load_trash_bin(location="A3")
    left_pipette = protocol.load_instrument(
        "flex_1channel_50",
        mount="left",
        tip_racks=[tips1,tips2]
    )

    # define reagents and labware 
    cells = protocol.load_labware("jd_24_tuberack_1.5ml", "B2")
    VacManifold = protocol.load_labware('jdvacuum_24_tuberack_500ul', 'B3')
    buffers = protocol.load_labware('jd_6_falconrack_50ml', 'C2')
    elution_tubes = protocol.load_labware('jd_24_tuberack_1.5ml', 'C3')

    # Calculate number of complete columns and remaining wells
    num_columns = num_samples // 4
    remaining_wells = num_samples % 4
    
    ### Process each column: Lyse then Neutralize before moving to next column ###
    # Process complete columns (4 wells each)
    for col in range(num_columns):
        column_wells = [cells.wells()[col * 4 + row] for row in range(4)]
        
        protocol.comment(f"Processing column {col + 1} - wells {[well.well_name for well in column_wells]}")
        
        ### 1. Lyse cells by adding 250ul Lysis buffer ###
        for well in column_wells:
            left_pipette.pick_up_tip()
            left_pipette.transfer(
                250,
                buffers["A1"].bottom(3) , 
                well.top(0),
                new_tip="never",
            )
            left_pipette.mix(3, 45, well)
            left_pipette.drop_tip()

        protocol.comment(f"Neutralizing column {col + 1}")

        ### 2. Neutralize by adding 350ul Neutralisation buffer ###
        for well in column_wells:
            left_pipette.pick_up_tip()
            left_pipette.transfer(
                350,
                buffers["A2"].bottom(3) , 
                well.top(0),
                new_tip="never", 
            )
            left_pipette.mix(3, 45, well)
            left_pipette.drop_tip()

    # Process remaining wells (if any)
    if remaining_wells > 0:
        start_well = num_columns * 4
        remaining_well_list = [cells.wells()[start_well + row] for row in range(remaining_wells)]
        
        protocol.comment(f"Processing remaining {remaining_wells} wells - {[well.well_name for well in remaining_well_list]}")
        
        ### 1. Lyse cells ###
        for well in remaining_well_list:
            left_pipette.pick_up_tip()
            left_pipette.transfer(
                250,
                buffers["A1"].bottom(3), 
                well.top(0),
                new_tip="never",
            )
            left_pipette.mix(3, 45, well)
            left_pipette.drop_tip()

        protocol.comment(f"Neutralizing remaining {remaining_wells} wells")

        ### 2. Neutralize ###
        for well in remaining_well_list:
            left_pipette.pick_up_tip()
            left_pipette.transfer(
                350,
                buffers["A2"].bottom(3), 
                well.top(0),
                new_tip="never", 
            )
            left_pipette.mix(3, 45, well)
            left_pipette.drop_tip()
    notify_slack("Lysis and Neutralization complete - Please proceed to spin down samples and load into vacuum manifold")
    ### Pause for user to spin down samples and load into vacuum manifold ###
    protocol.pause("Please spin down samples and load into vacuum manifold. Click Resume when ready.")

    ### 3. wash DNA - only for the number of samples being processed ###
    left_pipette.pick_up_tip()
    # First round of wash buffer
    for i in range(num_samples):
        left_pipette.transfer(
            500,
            buffers["A3"].bottom(3), 
            VacManifold.wells()[i].top(1),
            new_tip="never",
        )
    # Second round of wash buffer
    for i in range(num_samples):
        left_pipette.transfer(
            500,
            buffers["A3"].bottom(3), 
            VacManifold.wells()[i].top(1),
            new_tip="never",
        )
    left_pipette.drop_tip()
    notify_slack("Washing complete - Please proceed to elution steps")
    protocol.pause("Please transfer samples to elution tubes. Click Resume when ready.")

    ### 4. Elution - only for the number of samples being processed ###
    left_pipette.pick_up_tip()
    for i in range(num_samples):
        left_pipette.transfer(
            50,
            buffers["B1"].bottom(3), 
            elution_tubes.wells()[i].top(),
            new_tip="never"
        )
    left_pipette.drop_tip()
    notify_slack("Elution complete - Please proceed to final steps")
    # End of protocol
    protocol.comment(f"Protocol complete for {num_samples} samples. Spin down samples and store elutions at -20C")







    
