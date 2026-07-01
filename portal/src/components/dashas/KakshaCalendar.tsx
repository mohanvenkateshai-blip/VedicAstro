import React from 'react';
import { KakshaData } from '../../lib/types';

interface KakshaCalendarProps {
  data: KakshaData;
}

const KakshaCalendar: React.FC<KakshaCalendarProps> = ({ data }) => {
  return (
    <div className="kaksha-calendar">
      <h2>Kaksha Calendar</h2>
      <div className="calendar-grid">
        {data.kakshas.map((kaksha, index) => (
          <div key={index} className="kaksha-item">
            <div className="kaksha-name">{kaksha.name}</div>
            <div className="kaksha-duration">{kaksha.duration}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default KakshaCalendar;