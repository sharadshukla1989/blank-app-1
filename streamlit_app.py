import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

# Page configuration
st.set_page_config(page_title="Consolidation Analysis Dashboard", layout="wide")

# Add container image at the top
st.markdown("""
<div style='text-align: center; margin-bottom: 20px'>
    <svg width="200" height="100" viewBox="0 0 200 100">
        <!-- Container outline -->
        <rect x="50" y="10" width="100" height="80" fill="none" stroke="black" stroke-width="2"/>
        <!-- Half-filled area -->
        <rect x="50" y="50" width="100" height="40" fill="#e0e0e0"/>
        <!-- Label -->
        <text x="100" y="40" text-anchor="middle" fill="black">Under-utilized</text>
    </svg>
</div>
""", unsafe_allow_html=True)

def load_data():
    try:
        uploaded_file = st.sidebar.file_uploader("Upload shipping data CSV", type=['csv'])
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            
            # Convert dates using DD/MM/YYYY format
            date_columns = ['ETS', 'ETA', 'ATA']
            for col in date_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], format='%d/%m/%Y', dayfirst=True)
            
            return df
        else:
            st.warning("Please upload a CSV file")
            return None
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

def main():
    st.title("Shipping Consolidation Analysis")
    
    # Sidebar filters
    st.sidebar.header("Filters")
    
    # Load data
    df = load_data()
    if df is None:
        return
    
    # Date range type selector
    date_range_type = st.sidebar.selectbox(
        "Select Date Range Type",
        ["Week", "Month", "Quarter", "Year"]
    )
    
    # Add POL and POD filters
    pol_list = sorted(df['POL'].unique())
    pod_list = sorted(df['POD'].unique())
    
    selected_pol = st.sidebar.multiselect("Select Origin Ports (POL)", pol_list)
    selected_pod = st.sidebar.multiselect("Select Destination Ports (POD)", pod_list)
    
    # Filter data based on selections
    if selected_pol:
        df = df[df['POL'].isin(selected_pol)]
    if selected_pod:
        df = df[df['POD'].isin(selected_pod)]
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs([
        "Consolidation Analysis",
        "Movement Analysis",
        "Transit Time Analysis"
    ])
    
    with tab1:
        st.header("Consolidation Analysis")
        
        # Lane Analysis Section
        st.subheader("Lane Optimization Analysis")
        
        # Calculate weekly averages by lane and shipment type
        df['Week'] = df['ETS'].dt.isocalendar().week
        lane_analysis = df.groupby(['POL', 'POD', 'Week', 'Shipment Type'])['Volume in cbm'].sum().reset_index()
        
        # Calculate average weekly volumes
        lane_summary = lane_analysis.groupby(['POL', 'POD', 'Shipment Type']).agg({
            'Volume in cbm': ['mean', 'count']
        }).reset_index()
        
        # Rename columns for clarity
        lane_summary.columns = ['POL', 'POD', 'Shipment Type', 'Avg Weekly Volume', 'Weeks with Shipments']
        
        # Identify potential consolidation opportunities
        consolidation_opportunities = lane_summary[
            (lane_summary['Shipment Type'] == 'Carriers LCL') & 
            (lane_summary['Avg Weekly Volume'] >= 18)
        ].sort_values('Avg Weekly Volume', ascending=False)
        
        # Identify lanes that might be better for co-loading
        coload_opportunities = lane_summary[
            (lane_summary['Shipment Type'] == 'LCL') & 
            (lane_summary['Avg Weekly Volume'] < 18)
        ].sort_values('Avg Weekly Volume', ascending=False)
        
        # Display opportunities
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### Potential Consolidation Lanes (Currently Co-loaded)")
            st.dataframe(
                consolidation_opportunities[['POL', 'POD', 'Avg Weekly Volume', 'Weeks with Shipments']]
                .style.format({'Avg Weekly Volume': '{:.2f}'})
            )
        
        with col2:
            st.markdown("##### Potential Co-load Lanes (Currently Consolidated)")
            st.dataframe(
                coload_opportunities[['POL', 'POD', 'Avg Weekly Volume', 'Weeks with Shipments']]
                .style.format({'Avg Weekly Volume': '{:.2f}'})
            )
        
        # Visual comparison of lanes
        combined_opportunities = pd.concat([
            consolidation_opportunities.assign(Opportunity='Convert to Consolidation'),
            coload_opportunities.assign(Opportunity='Convert to Co-load')
        ])
        
        fig_lanes = px.scatter(
            combined_opportunities,
            x='POL',
            y='Avg Weekly Volume',
            color='Opportunity',
            size='Weeks with Shipments',
            hover_data=['POD', 'Avg Weekly Volume', 'Weeks with Shipments'],
            title='Lane Optimization Opportunities'
        )
        st.plotly_chart(fig_lanes)
        
        # Add summary metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Potential New Consolidation Lanes", len(consolidation_opportunities))
        with col2:
            st.metric("Potential New Co-load Lanes", len(coload_opportunities))
        with col3:
            total_volume_impact = (
                consolidation_opportunities['Avg Weekly Volume'].sum() +
                coload_opportunities['Avg Weekly Volume'].sum()
            )
            st.metric("Total Weekly Volume Impact", f"{total_volume_impact:.2f} CBM")
        
        # Consolidation vs Co-load comparison
        consol_data = df.groupby('Shipment Type')['Volume in cbm'].agg(['sum', 'count']).reset_index()
        
        # Bar chart for volume comparison
        fig_consol = px.bar(
            consol_data,
            x='Shipment Type',
            y='sum',
            title='Volume Comparison: Consolidation vs Co-load',
            labels={'sum': 'Total Volume (CBM)'}
        )
        st.plotly_chart(fig_consol)
        
        # Weekly consolidation opportunities
        df['Week'] = df['ETS'].dt.isocalendar().week
        weekly_vol = df[df['Shipment Type'] == 'LCL'].groupby(['POL', 'POD', 'Week'])['Volume in cbm'].sum().reset_index()
        
        # Identify consolidation opportunities
        weekly_vol['Opportunity'] = weekly_vol['Volume in cbm'].apply(
            lambda x: '40ft Container' if x >= 45 else '20ft Container' if x >= 18 else 'Combine Shipments'
        )
        
        st.subheader("Weekly Consolidation Opportunities")
        fig_weekly = px.scatter(
            weekly_vol,
            x='Week',
            y='Volume in cbm',
            color='Opportunity',
            hover_data=['POL', 'POD'],
            title='Weekly Volumes and Container Opportunities'
        )
        st.plotly_chart(fig_weekly)
        
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            total_volume = weekly_vol['Volume in cbm'].sum()
            st.metric("Total Volume (CBM)", f"{total_volume:,.2f}")
        with col2:
            potential_20ft = len(weekly_vol[weekly_vol['Volume in cbm'] >= 18])
            st.metric("Potential 20ft Containers", potential_20ft)
        with col3:
            potential_40ft = len(weekly_vol[weekly_vol['Volume in cbm'] >= 45])
            st.metric("Potential 40ft Containers", potential_40ft)
    
    with tab2:
        st.header("Movement Analysis")
        
        # Gateway vs CFS-CFS analysis
        movement_data = df[df['Shipment Type'] == 'LCL'].groupby('Movement')['Volume in cbm'].agg(['sum', 'count']).reset_index()
        
        # Create pie chart for movement distribution
        fig_movement = px.pie(
            movement_data,
            values='sum',
            names='Movement',
            title='Distribution of Movements (Gateway vs CFS-CFS)'
        )
        st.plotly_chart(fig_movement)
        
        # Monthly utilization analysis
        df['Month'] = df['ETS'].dt.to_period('M')
        monthly_util = df[df['Shipment Type'] == 'LCL'].groupby('Month')['Volume in cbm'].agg(['sum', 'count']).reset_index()
        monthly_util['Month'] = monthly_util['Month'].astype(str)
        
        fig_monthly = px.line(
            monthly_util,
            x='Month',
            y='sum',
            title='Monthly Consolidation Volume Trend'
        )
        st.plotly_chart(fig_monthly)
        
        # Movement summary metrics
        col1, col2 = st.columns(2)
        with col1:
            gateway_pct = (movement_data[movement_data['Movement'].str.contains('Gateway', na=False)]['sum'].sum() / 
                         movement_data['sum'].sum() * 100)
            st.metric("Gateway Shipments %", f"{gateway_pct:.1f}%")
        with col2:
            cfs_pct = (movement_data[movement_data['Movement'].str.contains('CFS', na=False)]['sum'].sum() / 
                      movement_data['sum'].sum() * 100)
            st.metric("CFS-CFS Shipments %", f"{cfs_pct:.1f}%")
    
    with tab3:
        st.header("Transit Time Analysis")
        
        # Calculate transit times
        df['Transit Days'] = (df['ATA'] - df['ETS']).dt.days
        
        # Transit time distribution
        fig_transit = px.box(
            df,
            x='POL',
            y='Transit Days',
            color='POD',
            title='Transit Time Distribution by Route'
        )
        st.plotly_chart(fig_transit)
        
        # Transit time gap analysis
        transit_gap = df.groupby(['POL', 'POD'])['Transit Days'].agg(['mean', 'min', 'max']).reset_index()
        
        fig_gap = px.bar(
            transit_gap,
            x='POL',
            y='mean',
            error_y='max',
            error_y_minus='min',
            color='POD',
            title='Transit Time Analysis by Route'
        )
        st.plotly_chart(fig_gap)
        
        # Transit time summary metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            avg_transit = df['Transit Days'].mean()
            st.metric("Average Transit Days", f"{avg_transit:.1f}")
        with col2:
            min_transit = df['Transit Days'].min()
            st.metric("Minimum Transit Days", min_transit)
        with col3:
            max_transit = df['Transit Days'].max()
            st.metric("Maximum Transit Days", max_transit)

if __name__ == "__main__":
    main()
